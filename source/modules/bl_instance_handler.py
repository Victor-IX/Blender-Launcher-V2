from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from windows.popup_window import PopupIcon, PopupWindow

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class BLInstanceHandler(QObject):
    """
    Manages the singleton behavior of Blender launcher.

    This class ensures that only one instance of the launcher is running at a time.
    If another instance of the launcher tries to start, it will find this one and stop initialization.
    """

    show_launcher = Signal()

    def __init__(self, launcher: BlenderLauncher):
        super().__init__(launcher)
        self.launcher = launcher
        self.server = QLocalServer(self)
        self.server.listen("blender-launcher-server")
        self.server.newConnection.connect(self.new_connection)

    def new_connection(self):
        socket = self.server.nextPendingConnection()
        assert socket is not None
        socket.readyRead.connect(lambda: self.read_socket_data(socket))
        self.show_launcher.emit()

    def read_socket_data(self, socket: QLocalSocket):
        data = socket.readAll()

        if str(data.data(), encoding="ascii") != str(self.launcher.version):
            self.dlg = PopupWindow(
                parent=self.launcher,
                title="Warning",
                message="An attempt to launch a different version<br>\
                      of Blender Launcher was detected!<br>\
                      Please, terminate currently running<br>\
                      version to proceed this action!",
                info_popup=True,
                icon=PopupIcon.WARNING,
            )
