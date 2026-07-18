from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from i18n import t
from modules.platform_utils import get_platform
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSystemTrayIcon
from widgets.base_menu_widget import BaseMenuWidget

if TYPE_CHECKING:
    from widgets.library_widget import LibraryWidget

    from .window import BlenderLauncher


class TrayHandler(QObject):
    quit = Signal()
    close = Signal()
    trigger = Signal()
    favs = Signal()
    quick_launch = Signal()

    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent)

        self.launcher: BlenderLauncher = parent

        # Setup tray icon context Menu
        quit_action = QAction(t("act.quit"), self)
        quit_action.triggered.connect(self.quit)
        hide_action = QAction(t("act.hide"), self)
        hide_action.triggered.connect(self.close)
        show_action = QAction(t("act.show"), self)
        show_action.triggered.connect(self.trigger)
        show_favorites_action = QAction(self.launcher.icons.favorite, t("act.tabs.favorites"), self)
        show_favorites_action.triggered.connect(self.favs)

        self.static_actions = [show_favorites_action, show_action, hide_action, quit_action]
        self.quick_launch_actions: list[QAction] = []

        self.tray_menu = BaseMenuWidget(parent=self.launcher)
        self.tray_menu.setFont(parent.fonts.font_10)
        self.tray_menu.addActions(self.static_actions)

        self.launcher.quick_launch_handler.builds_changed.connect(self.rebuild_quick_launch_actions)
        self.rebuild_quick_launch_actions()

        # Setup tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.launcher.icons.taskbar)
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
            if get_platform() == "macOS":
                # Defer the macOS tray popup so Quit can exit properly.
                QTimer.singleShot(0, self.tray_menu.trigger)
            else:
                self.tray_menu.trigger()

    def rebuild_quick_launch_actions(self):
        for action in self.quick_launch_actions:
            self.tray_menu.removeAction(action)
            action.deleteLater()
        self.quick_launch_actions.clear()

        builds = self.launcher.quick_launch_handler.quick_launch_builds
        before = self.static_actions[0]

        for build in builds:
            action = QAction(self.launcher.icons.quick_launch, self._quick_launch_label(build), self)
            action.triggered.connect(partial(self.launcher.quick_launch_handler.quick_launch, build))
            self.tray_menu.insertAction(before, action)
            self.quick_launch_actions.append(action)

        if builds:
            separator = QAction(self)
            separator.setSeparator(True)
            self.tray_menu.insertAction(before, separator)
            self.quick_launch_actions.append(separator)

    @staticmethod
    def _quick_launch_label(build: LibraryWidget) -> str:
        info = build.build_info
        return f"Blender {info.display_version} ({info.custom_name or info.display_label})"

    def set_visible(self, b: bool):
        if b:
            self.tray_icon.show()
        else:
            self.tray_icon.hide()

    def message(self, msg: str):
        self.tray_icon.showMessage(
            "Blender Launcher",
            msg,
            self.launcher.icons.taskbar,
            10000,
        )
