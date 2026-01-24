from enum import Enum
from typing import Generic

from modules.settings import get_column_widths, get_list_sorting_type, set_column_widths, set_list_sorting_type
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget
from widgets.base_list_widget import _WT, BaseListWidget


class SortingType(Enum):
    DATETIME = 1
    VERSION = 2
    LABEL = 3


SHOW_RELOAD_ON = {
    "custom",
}


class BasePageWidget(QWidget, Generic[_WT]):
    # Signal emitted when column widths change: (version_width, branch_width, commit_time_width)
    column_widths_changed = Signal(int, int, int)

    # Default column widths
    DEFAULT_VERSION_WIDTH = 85
    DEFAULT_BRANCH_WIDTH = 200
    DEFAULT_COMMIT_TIME_WIDTH = 118

    def __init__(self, parent, page_name, time_label, info_text, show_reload=False, extended_selection=False):
        super().__init__(parent)
        self.name = page_name

        # Debounce timer for saving column widths
        self._save_widths_timer = QTimer(self)
        self._save_widths_timer.setSingleShot(True)
        self._save_widths_timer.setInterval(200)
        self._save_widths_timer.timeout.connect(self._save_column_widths)

        self.sort_order_asc = True

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Placeholder Widget
        self.PlaceholderWidget = QWidget()
        self.PlaceholderWidget.setProperty("ToolBoxWidget", True)
        self.PlaceholderLayout = QVBoxLayout(self.PlaceholderWidget)
        self.PlaceholderLayout.setContentsMargins(0, 0, 0, 0)

        self.InfoPixmap = QPixmap(":resources/icons/info.svg")
        self.InfoPixmapLabel = QLabel()
        self.InfoPixmapLabel.setScaledContents(True)
        self.InfoPixmapLabel.setFixedSize(32, 32)
        self.InfoPixmapLabel.setPixmap(self.InfoPixmap)

        self.InfoLabelLayout = QHBoxLayout()
        self.InfoLabelLayout.setContentsMargins(0, 0, 0, 6)
        self.InfoLabel = QLabel(info_text)
        self.InfoLabelLayout.addWidget(self.InfoLabel)

        self.list_widget: BaseListWidget[_WT] = BaseListWidget(self, extended_selection=extended_selection)
        self.list_widget.hide()

        self.InfoLayout = QHBoxLayout()
        self.InfoLayout.setContentsMargins(0, 0, 0, 0)

        self.InfoLayout.addStretch()
        self.InfoLayout.addWidget(self.InfoPixmapLabel)
        self.InfoLayout.addLayout(self.InfoLabelLayout)
        self.InfoLayout.addStretch()

        self.PlaceholderLayout.addStretch()
        self.PlaceholderLayout.addLayout(self.InfoLayout)

        self.EmptyReloadButton = QPushButton("Reload")
        self.EmptyReloadButton.setToolTip("Reload Custom builds from disk")
        self.EmptyReloadButton.clicked.connect(parent.reload_custom_builds)
        self.EmptyReloadButton.hide()

        self.ReloadBtnLayout = QHBoxLayout()
        self.ReloadBtnLayout.addStretch()
        self.ReloadBtnLayout.addWidget(self.EmptyReloadButton)
        self.ReloadBtnLayout.addStretch()

        self.PlaceholderLayout.addLayout(self.ReloadBtnLayout)
        self.PlaceholderLayout.addStretch()

        # Header Widget
        self.HeaderWidget = QWidget()
        self.HeaderWidget.hide()
        self.HeaderWidget.setProperty("ToolBoxWidget", True)
        self.HeaderLayout = QHBoxLayout(self.HeaderWidget)
        self.HeaderLayout.setContentsMargins(2, 0, 0, 0)
        self.HeaderLayout.setSpacing(0)

        self.HeaderReloadButton = QPushButton("Reload")
        self.HeaderReloadButton.setToolTip("Reload Custom builds from disk")
        self.HeaderReloadButton.setProperty("ListHeader", True)
        self.HeaderReloadButton.clicked.connect(parent.reload_custom_builds)
        self.HeaderReloadButton.setFixedWidth(95)  # Match launchButton width in list items

        # Create splitter for resizable columns
        self.headerSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.headerSplitter.setHandleWidth(3)
        self.headerSplitter.setChildrenCollapsible(False)

        self.subversionLabel = QPushButton("Version")
        self.subversionLabel.setMinimumWidth(60)
        self.subversionLabel.setProperty("ListHeader", True)
        self.subversionLabel.setCheckable(True)
        self.subversionLabel.clicked.connect(lambda: self.set_sorting_type(SortingType.VERSION))

        self.branchLabel = QPushButton("Branch")
        self.branchLabel.setMinimumWidth(80)
        self.branchLabel.setProperty("ListHeader", True)
        self.branchLabel.setCheckable(True)
        self.branchLabel.clicked.connect(lambda: self.set_sorting_type(SortingType.LABEL))

        self.commitTimeLabel = QPushButton(time_label)
        self.commitTimeLabel.setMinimumWidth(80)
        self.commitTimeLabel.setProperty("ListHeader", True)
        self.commitTimeLabel.setCheckable(True)
        self.commitTimeLabel.clicked.connect(lambda: self.set_sorting_type(SortingType.DATETIME))

        self.headerSplitter.addWidget(self.subversionLabel)
        self.headerSplitter.addWidget(self.branchLabel)
        self.headerSplitter.addWidget(self.commitTimeLabel)

        # Set stretch factors: version and commit time stay fixed, branch stretches
        self.headerSplitter.setStretchFactor(0, 0)  # Version
        self.headerSplitter.setStretchFactor(1, 1)  # Branch
        self.headerSplitter.setStretchFactor(2, 0)  # Commit time

        # Load saved column widths or use defaults
        saved_widths = get_column_widths()
        if saved_widths:
            self.headerSplitter.setSizes(saved_widths)
        else:
            self.headerSplitter.setSizes(
                [self.DEFAULT_VERSION_WIDTH, self.DEFAULT_BRANCH_WIDTH, self.DEFAULT_COMMIT_TIME_WIDTH]
            )

        # Connect splitter movement to emit signal and save
        self.headerSplitter.splitterMoved.connect(self._on_splitter_moved)

        self.HeaderLayout.addWidget(self.HeaderReloadButton)
        self.HeaderLayout.addWidget(self.headerSplitter, stretch=1)
        self.HeaderLayout.addSpacing(34)

        # Final layout
        self.layout.addWidget(self.HeaderWidget)
        self.layout.addWidget(self.PlaceholderWidget)
        self.layout.addWidget(self.list_widget)

        self.sorting_type = SortingType(get_list_sorting_type(self.name))
        self.sorting_order = Qt.SortOrder.DescendingOrder
        self.set_sorting_type(self.sorting_type)

    def set_info_label_text(self, text):
        self.InfoLabel.setText(text)

    def set_sorting_type(self, sorting_type):
        if sorting_type == self.sorting_type:
            self.sorting_order = (
                Qt.SortOrder.DescendingOrder
                if self.sorting_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self.sorting_order = Qt.SortOrder.AscendingOrder

        self.sorting_type = sorting_type
        self.list_widget.sortItems(self.sorting_order)

        self.commitTimeLabel.setChecked(sorting_type == SortingType.DATETIME)
        self.subversionLabel.setChecked(sorting_type == SortingType.VERSION)
        self.branchLabel.setChecked(sorting_type == SortingType.LABEL)

        set_list_sorting_type(self.name, sorting_type)

    def update_reload(self, branch: tuple[str, ...]):
        visible = len(set(branch) & SHOW_RELOAD_ON) > 0
        self.EmptyReloadButton.setVisible(visible)
        self.HeaderReloadButton.setText("Reload" * visible)
        self.HeaderReloadButton.setEnabled(visible)

    def _on_splitter_moved(self, pos, index):
        """Handle splitter movement - debounce save and emit signal."""
        sizes = self.headerSplitter.sizes()
        self._save_widths_timer.start()  # Restart debounce timer
        self.column_widths_changed.emit(sizes[0], sizes[1], sizes[2])

    def _save_column_widths(self):
        """Save column widths to settings (called after debounce)."""
        sizes = self.headerSplitter.sizes()
        set_column_widths(sizes)

    def resizeEvent(self, event):
        """Emit column width changes when the widget is resized."""
        super().resizeEvent(event)
        sizes = self.headerSplitter.sizes()
        self.column_widths_changed.emit(sizes[0], sizes[1], sizes[2])

    def get_column_widths(self) -> tuple[int, int, int]:
        """Return current column widths (version, branch, commit_time)."""
        sizes = self.headerSplitter.sizes()
        return (sizes[0], sizes[1], sizes[2])
