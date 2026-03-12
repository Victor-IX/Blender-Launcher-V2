from typing import TYPE_CHECKING

from i18n import t
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QStatusBar,
)

if TYPE_CHECKING:
    from .window import BlenderLauncher


class LauncherStatusBar(QStatusBar):
    force_check = Signal()
    update = Signal(bool)

    def __init__(self, parent: "BlenderLauncher"):
        super().__init__(parent)

        self.version = parent.version
        self.setContentsMargins(0, 0, 0, 2)
        self.setFont(parent.fonts.font_10)

        self.status = "????"

        self.statusbar_label = QLabel(self.status, self)
        self.force_check_button = QPushButton(t("act.a.check"), self)
        self.force_check_button.setToolTip(t("act.a.check_tooltip"))
        self.force_check_button.setEnabled(False)

        self.force_check_button.clicked.connect(self.force_check)
        self.new_version_button = QPushButton(self)
        self.new_version_button.setToolTip(t("act.a.version_tooltip"))
        self.new_version_button.hide()
        self.new_version_button.clicked.connect(self.update)
        self.statusbar_version = QPushButton(str(self.version), self)
        self.statusbar_version.setToolTip(t("act.a.version_tooltip"))
        self.statusbar_version.clicked.connect(self.changelog)

        self.addWidget(self.force_check_button)
        self.addWidget(QLabel("│"))
        self.addWidget(self.statusbar_label)

        self.addPermanentWidget(self.new_version_button)
        self.addPermanentWidget(self.statusbar_version)

    @Slot()
    def changelog(self):
        url = f"https://github.com/Victor-IX/Blender-Launcher-V2/releases/tag/v{self.version!s}"
        QDesktopServices.openUrl(url)

    def set_status(self, status=None, force_check_on=None):
        if status is not None:
            self.status = status

        if force_check_on is not None:
            self.force_check_button.setEnabled(force_check_on)

        self.statusbar_label.setText(self.status)

    def new_version(self, tag: str):
        self.new_version_button.setText(t("msg.updates.update_to_version", version=tag.replace("v", "")))
        self.new_version_button.show()

    def no_new_version(self):
        self.new_version_button.hide()
