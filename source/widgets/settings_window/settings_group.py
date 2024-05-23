from __future__ import annotations

from modules.icons import Icons
from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QLocalServer
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsGroup(QFrame):
    collapsed = pyqtSignal(bool)
    checked = pyqtSignal(bool)

    def __init__(self, label: str, *, checkable=False, icons: Icons | None = None, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        # self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setProperty("SettingsGroup", True)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)

        if icons is None:
            icons = Icons.get()

        self._collapse_icon = icons.expand_less
        self._uncollapse_icon = icons.expand_more

        self.collapse_button = QPushButton(parent)
        self.collapse_button.setProperty("CollapseButton", True)
        self.collapse_button.setMaximumSize(20, 20)
        self.collapse_button.setIcon(self._collapse_icon)
        self.collapse_button.clicked.connect(self.toggle)
        self._checkable = checkable

        self._layout.addWidget(self.collapse_button, 0, 0, 1, 1)

        if checkable:
            self.checkbutton = QCheckBox(self)
            self.label = None
            self.checkbutton.setText(label)
            self.checkbutton.clicked.connect(self.checked.emit)
            self._layout.addWidget(self.checkbutton, 0, 1, 1, 1)

        else:
            self.checkbutton = None
            self.label = QLabel(f" {label}")
            self._layout.addWidget(self.label, 0, 1, 1, 1)

        self._widget = None
        self._collapsed = False

    @pyqtSlot(QWidget)
    def setWidget(self, w: QWidget):
        if self._widget == w:
            return

        if self._widget is not None:
            self._layout.removeWidget(self._widget)
        self._widget = w
        self._layout.addWidget(self._widget, 1, 0, 1, 2)

    @pyqtSlot(QLayout)
    def setLayout(self, layout: QLayout):
        if self._widget is not None:
            self._layout.removeWidget(self._widget)
        self._widget = QWidget()
        self._widget.setLayout(layout)
        self._layout.addWidget(self._widget, 1, 0, 1, 2)

    @pyqtSlot(bool)
    def set_collapsed(self, b: bool):
        if b and not self._collapsed:
            self.collapse()
            self._collapsed = True
        elif self._collapsed:
            self.uncollapse()
            self._collapsed = False

    @pyqtSlot()
    def toggle(self):
        self.set_collapsed(not self._collapsed)

    @pyqtSlot()
    def collapse(self):
        assert self._widget is not None
        self._widget.hide()
        self.collapse_button.setIcon(self._uncollapse_icon)
        self._collapsed = True
        self.collapsed.emit(True)

    @pyqtSlot()
    def uncollapse(self):
        assert self._widget is not None
        self._widget.show()
        self.collapse_button.setIcon(self._collapse_icon)
        self._collapsed = False
        self.collapsed.emit(False)
