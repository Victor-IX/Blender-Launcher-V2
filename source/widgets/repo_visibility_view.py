from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class RepoUserView(QWidget):
    library_changed = Signal(bool)
    download_changed = Signal(bool)

    def __init__(
        self,
        name: str,
        description: str = "",
        library: bool | None = True,  # bool if used, None if disabled
        download: bool | None = True,  # bool if used, None if disabled
        bind_download_to_library: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
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
        self.library_enable_button.setToolTip(
            "Make this repository visible / hidden in the launcher view.<br>\
            If disabled, then it will automatically disable fetching,<br>\
            unless another repository shares the fetching behavior."
        )
        self.library_enable_button.toggled.connect(self.__library_button_toggled)

        if library is None:
            self.library_enable_button.setEnabled(False)

        self.download_enable_button = QCheckBox(self)
        self.download_enable_button.setProperty("Download", True)
        self.download_enable_button.setChecked(download or False)
        self.download_enable_button.setToolTip(
            'Enable / Disable fetching this repository.<br>\
            If you force-check by holding SHIFT while pressing the "Check" button,<br>\
            Then all visible categories will download regardless of fetching settings.'
        )
        self.download_enable_button.toggled.connect(self.__download_button_toggled)
        self.previous_download = download or False

        if download is None:
            self.download_enable_button.setEnabled(False)

        self.bind_download_to_library = bind_download_to_library

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

    def __library_button_toggled(self, checked: bool):
        self.title_label.setEnabled(checked)
        if self.bind_download_to_library:
            self.__library_bound_toggle(checked)
        self.library_changed.emit(checked)

    def __download_button_toggled(self, checked: bool):
        if not self.library_enable_button.isChecked() and checked:
            self.library_enable_button.setChecked(True)
        self.download_enable_button.setChecked(checked)
        self.download_changed.emit(checked)

    def __library_bound_toggle(self, b: bool):
        if not b:
            self.previous_download = self.download_enable_button.isChecked()
            self.download_enable_button.setChecked(False)
        else:
            self.download_enable_button.setChecked(self.previous_download)

    def __library_toggled(self, btn: QCheckBox, checked: bool):
        if btn is not self and checked != self.library_enable_button.isChecked():
            self.library_enable_button.setChecked(checked)

    def __download_toggled(self, btn: QCheckBox, checked: bool):
        if btn is not self and checked != self.download_enable_button.isChecked():
            self.download_enable_button.setChecked(checked)

    @property
    def download(self):
        return self.download_enable_button.isChecked()

    @download.setter
    def download(self, v: bool):
        self.download_enable_button.setChecked(v)

    @property
    def library(self):
        return self.library_enable_button.isChecked()
