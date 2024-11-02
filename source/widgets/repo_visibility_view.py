from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class RepoUserView(QWidget):
    library_changed = pyqtSignal(bool)
    download_changed = pyqtSignal(bool)

    def __init__(
        self,
        name: str,
        description: str = "",
        library: bool | None = True,  # bool if used, None if disabled
        download: bool | None = True,  # bool if used, None if disabled
        parent=None,
    ):
        super().__init__(parent)
        self.name = name

        self.title_label = QLabel(name, self)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        font = QFont(self.title_label.font())
        font.setPointSize(11)
        self.title_label.setFont(font)
        if description:
            self.title_label.setToolTip(description)

        self.library_enable_button = QCheckBox(self)
        self.library_enable_button.setProperty("Visibility", True)
        self.library_enable_button.setChecked(library or False)
        self.library_enable_button.setText(None)
        self.library_enable_button.toggled.connect(self.library_changed)

        if library is None:
            self.library_enable_button.setEnabled(False)

        self.download_enable_button = QCheckBox(self)
        self.download_enable_button.setProperty("Download", True)
        self.download_enable_button.setChecked(download or False)
        self.download_enable_button.setText(None)
        self.download_enable_button.toggled.connect(self.download_changed)

        if download is None:
            self.download_enable_button.setEnabled(False)

        self.layout_ = QGridLayout(self)
        self.layout_.setContentsMargins(5, 5, 0, 5)
        self.layout_.setSpacing(5)
        self.layout_.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.layout_.addWidget(self.title_label, 0, 0, 1, 1)
        self.layout_.addWidget(self.library_enable_button, 0, 1, 1, 1)
        self.layout_.addWidget(self.download_enable_button, 0, 2, 1, 1)

    def add_library_to_group(self, grp: QButtonGroup):
        grp.addButton(self.library_enable_button)
        grp.buttonToggled.connect(self.__library_toggled)

    def add_downloads_to_group(self, grp: QButtonGroup):
        grp.addButton(self.download_enable_button)
        grp.buttonToggled.connect(self.__download_toggled)

    def __library_toggled(self, btn: QCheckBox, checked: bool):
        if btn is not self and checked != self.library_enable_button.isChecked():
            self.library_enable_button.setChecked(checked)

    def __download_toggled(self, btn: QCheckBox, checked: bool):
        if btn is not self and checked != self.download_enable_button.isChecked():
            self.download_enable_button.setChecked(checked)

    @property
    def download(self):
        return self.download_enable_button.isChecked()

    @property
    def library(self):
        return self.library_enable_button.isChecked()
