from __future__ import annotations

from typing import TYPE_CHECKING

from modules.connection_manager import ConnectionManager
from modules.icons import Icons
from modules.settings import get_enable_high_dpi_scaling, get_use_system_titlebar
from PySide6.QtCore import QFile, QPoint, Qt, QTextStream
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMainWindow

if TYPE_CHECKING:
    from semver import Version

if get_enable_high_dpi_scaling():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)


class BaseWindow(QMainWindow):
    def __init__(self, parent=None, app: QApplication | None = None, version: Version | None = None):
        super().__init__()
        self.parent = parent

        # Setup icons
        self.icons = Icons.get()

        if parent is None and app is not None:
            self.app = app
            self.version = version

            # Setup pool manager
            self.cm = ConnectionManager(version=version)
            self.cm.setup()
            self.manager = self.cm.manager

            # Setup font
            QFontDatabase.addApplicationFont(":resources/fonts/OpenSans-SemiBold.ttf")
            self.font_10 = QFont("Open Sans SemiBold", 10)
            self.font_10.setHintingPreference(QFont.PreferNoHinting)
            self.font_8 = QFont("Open Sans SemiBold", 8)
            self.font_8.setHintingPreference(QFont.PreferNoHinting)
            self.app.setFont(self.font_10)

            # Setup style
            file = QFile(":resources/styles/global.qss")
            file.open(QFile.ReadOnly | QFile.Text)
            self.style_sheet = QTextStream(file).readAll()
            self.app.setStyleSheet(self.style_sheet)

        self.using_system_bar = get_use_system_titlebar()
        self.set_system_titlebar(self.using_system_bar)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.pos = self.pos()
        self.pressing = False

        self.destroyed.connect(lambda: self._destroyed())

    def set_system_titlebar(self, b: bool):
        """
        Changes window flags so frameless is enabled (custom headers) or disabled (system).

        This is called during initialization. use update_system_titlebar(b: bool) to update window components.

        Arguments:
            b -- bool
        """
        if not b:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            if self.using_system_bar:
                self.hide()
                self.show()
            self.using_system_bar = False
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.FramelessWindowHint)  # type: ignore
            if not self.using_system_bar:
                self.hide()
                self.show()
            self.using_system_bar = True

    def update_system_titlebar(self, b: bool):
        """
        Used to update window components, such as the header, when swapping between the system title bar and
        the custom one

        Arguments:
            b -- bool
        """

    def mousePressEvent(self, event):
        self.pos = event.globalPos()
        self.pressing = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.pressing:
            delta = QPoint(event.globalPos() - self.pos)
            self.moveWindow(delta, True)
            self.pos = event.globalPos()

    def moveWindow(self, delta, chain=False):
        self.move(self.x() + delta.x(), self.y() + delta.y())

        if chain and self.parent is not None:
            for window in self.parent.windows:
                if window is not self:
                    window.moveWindow(delta)

    def mouseReleaseEvent(self, _event):
        self.pressing = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def showEvent(self, event):
        parent = self.parent

        if parent is not None:
            if self not in parent.windows:
                parent.windows.append(self)
                parent.show_signal.connect(self.show)
                parent.close_signal.connect(self.hide)

            if self.parent.isVisible():
                x = parent.x() + (parent.width() - self.width()) * 0.5
                y = parent.y() + (parent.height() - self.height()) * 0.5
            else:
                size = parent.app.screens()[0].size()
                x = (size.width() - self.width()) * 0.5
                y = (size.height() - self.height()) * 0.5

            self.move(int(x), int(y))
            event.accept()

    def _destroyed(self):
        if self.parent is not None and self in self.parent.windows:
            self.parent.windows.remove(self)
