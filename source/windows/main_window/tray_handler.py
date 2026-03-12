from functools import wraps
from typing import TYPE_CHECKING

from i18n import t
from modules.platform_utils import get_platform
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QSystemTrayIcon
from widgets.base_menu_widget import BaseMenuWidget

if TYPE_CHECKING:
    from .window import BlenderLauncher


class TrayHandler(QObject):
    """ """

    quit = Signal()
    close = Signal()
    trigger = Signal()
    favs = Signal()
    quick_launch = Signal()

    def __init__(self, parent: "BlenderLauncher"):
        super().__init__(parent)

        # Setup tray icon context Menu
        quit_action = QAction(t("act.quit"), self)
        quit_action.triggered.connect(self.quit)
        hide_action = QAction(t("act.hide"), self)
        hide_action.triggered.connect(self.close)
        show_action = QAction(t("act.show"), self)
        show_action.triggered.connect(self.trigger)
        show_favorites_action = QAction(self.parent().icons.favorite, "Favorites", self)
        show_favorites_action.triggered.connect(self.favs)
        quick_launch_action = QAction(self.parent().icons.quick_launch, "Blender", self)
        quick_launch_action.triggered.connect(self.quick_launch)

        self.tray_menu = BaseMenuWidget(parent=self.parent())
        self.tray_menu.setFont(parent.fonts.font_10)
        self.tray_menu.addActions(
            [
                quick_launch_action,
                show_favorites_action,
                show_action,
                hide_action,
                quit_action,
            ]
        )

        # Setup tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.parent().icons.taskbar)
        self.tray_icon.setToolTip("Blender Launcher")
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.messageClicked.connect(self.trigger)

        # Linux doesn't handle QSystemTrayIcon.Context activation reason,
        # so add context menu as regular one
        if get_platform() == "Linux":
            self.tray_icon.setContextMenu(self.tray_menu)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.trigger.emit()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.quick_launch.emit()
            # INFO: Middle click dose not work anymore on new Windows versions with PyQt5
            # Middle click currently returns the Trigger reason
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.tray_menu.trigger()

    def set_visible(self, b: bool):
        if b:
            self.tray_icon.show()
        else:
            self.tray_icon.hide()

    def message(self, msg: str):
        self.tray_icon.showMessage(
            "Blender Launcher",
            msg,
            icon=self.parent().icons.taskbar,  # type: ignore
            msecs=10000,
        )
