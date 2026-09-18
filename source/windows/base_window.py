from __future__ import annotations

from typing import TYPE_CHECKING

from modules.fonts import Fonts
from modules.icons import Icons
from modules.settings import get_use_system_titlebar
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

if TYPE_CHECKING:
    from semver import Version
    from windows.main_window import BlenderLauncher


WINDOW_COLLECTION: list[BaseWindow] = []
# Window collections used to translate all windows at the same time.


class BaseWindow(QMainWindow):
    def __init__(
        self,
        window_collection: list[BaseWindow] = WINDOW_COLLECTION,
    ):
        super().__init__()

        # Setup icons & fonts
        self.icons = Icons.get()
        self.fonts = Fonts.get()

        self.using_system_bar = get_use_system_titlebar()
        self.set_system_titlebar(self.using_system_bar)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.window_collection = window_collection
        window_collection.append(self)

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
        if not self.window_collection:
            super().showEvent(event)
            return

        # Primary window, typically the Launcher window, is in the first index
        authority = self.window_collection[0]
        if self not in self.window_collection:
            self.window_collection.append(self)

        if authority.isVisible():
            x = authority.x() + (authority.width() - self.width()) * 0.5
            y = authority.y() + (authority.height() - self.height()) * 0.5
            screen = authority.screen() or QApplication.primaryScreen()
        else:
            screen = QApplication.primaryScreen()
            geo = screen.availableGeometry()
            x = geo.left() + (geo.width() - self.width()) * 0.5
            y = geo.top() + (geo.height() - self.height()) * 0.5

        # Clamp to the screen's available area so the header stays reachable when the
        # window is taller than the screen (e.g. macOS with a high DPI scale factor).
        avail = screen.availableGeometry()
        max_x = avail.left() + max(0, avail.width() - self.width())
        max_y = avail.top() + max(0, avail.height() - self.height())
        x = max(avail.left(), min(int(x), max_x))
        y = max(avail.top(), min(int(y), max_y))

        self.move(x, y)
        event.accept()
        return

    def _destroyed(self):
        self.window_collection.remove(self)
