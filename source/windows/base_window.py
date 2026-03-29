from __future__ import annotations

from typing import TYPE_CHECKING

from modules.connection_manager import ConnectionManager
from modules.fonts import Fonts
from modules.icons import Icons
from modules.settings import get_use_system_titlebar
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

if TYPE_CHECKING:
    from semver import Version
    from windows.main_window import BlenderLauncher


class BaseWindow(QMainWindow):
    def __init__(
        self, parent: BlenderLauncher | None = None, app: QApplication | None = None, version: Version | None = None
    ):
        super().__init__()
        if parent is not None:
            self.launcher: BlenderLauncher = parent

        # Setup icons & fonts
        self.icons = Icons.get()
        self.fonts = Fonts.get()

        if parent is None and app is not None and version is not None:
            self.app = app
            self.version = version

            # Setup pool manager
            self.cm = ConnectionManager(version=version)
            self.cm.setup()
            self.manager = self.cm.manager

        self.using_system_bar = get_use_system_titlebar()
        self.set_system_titlebar(self.using_system_bar)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.pressing = False

        self.destroyed.connect(lambda: self._destroyed())

    def set_system_titlebar(self, use_system_bar: bool):
        """
        Changes window flags so frameless is enabled (custom headers) or disabled (system).

        This is called during initialization. use update_system_titlebar(b: bool) to update window components.

        Arguments:
            b -- bool
        """
        if use_system_bar != self.using_system_bar:
            self.using_system_bar = use_system_bar

            if use_system_bar:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
            else:
                self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

            self.hide()
            self.show()
        elif not use_system_bar:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            if self.using_system_bar:
                self.hide()
                self.show()
            self.using_system_bar = False

    def update_system_titlebar(self, b: bool):
        """
        Used to update window components, such as the header, when swapping between the system title bar and
        the custom one

        Arguments:
            b -- bool
        """

    def mousePressEvent(self, event):
        self.pressing = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.windowHandle().startSystemMove()

    def mouseReleaseEvent(self, _event):
        self.pressing = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def showEvent(self, event):
        if hasattr(self, "launcher") and self.launcher is not None:
            launcher = self.launcher
            if self not in launcher.windows:
                launcher.windows.append(self)
                launcher.show_signal.connect(self.show)
                launcher.close_signal.connect(self.hide)

            if launcher.isVisible():
                x = launcher.x() + (launcher.width() - self.width()) * 0.5
                y = launcher.y() + (launcher.height() - self.height()) * 0.5
            else:
                size = launcher.app.screens()[0].size()
                x = (size.width() - self.width()) * 0.5
                y = (size.height() - self.height()) * 0.5

            self.move(int(x), int(y))
            event.accept()

    def _destroyed(self):
        if hasattr(self, "launcher") and self.launcher is not None and self in self.launcher.windows:
            self.launcher.windows.remove(self)
