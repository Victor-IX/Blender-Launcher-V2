from __future__ import annotations

from typing import TYPE_CHECKING

from i18n import t
from modules.icons import Icons
from modules.settings import (
    get_github_token,
    get_proxy_host,
    get_proxy_password,
    get_proxy_port,
    get_proxy_type,
    get_proxy_user,
    get_use_custom_tls_certificates,
    get_user_id,
    proxy_types,
    set_github_token,
    set_proxy_host,
    set_proxy_password,
    set_proxy_port,
    set_proxy_type,
    set_proxy_user,
    set_use_custom_tls_certificates,
    set_user_id,
)
from PySide6 import QtGui
from PySide6.QtCore import QRegularExpression, QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QPushButton,
)
from widgets.settings_form_widget import SettingsFormWidget
from windows.popup_window import Popup

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class ConnectionTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Get icons
        self.icons = Icons.get()

        # Authentication
        with self.group("settings.connection.authentication_settings") as grp:
            # User ID
            self.UserIDLineEdit = grp.add(QLineEdit(), "settings.connection.user_id")
            self.UserIDLineEdit.setText(get_user_id())
            self.UserIDLineEdit.setToolTip(t("settings.connection.user_id_tooltip"))

            rx = QRegularExpression(r"^[a-zA-Z0-9-]{8,64}$")

            self.user_id_validator = QtGui.QRegularExpressionValidator(rx, self)
            self.UserIDLineEdit.setValidator(self.user_id_validator)
            self.UserIDLineEdit.editingFinished.connect(self.update_user_id)

            # GitHub Token
            with grp.hgroup("settings.connection.github_token") as gt:
                self.GitHubTokenLineEdit = gt.add(QLineEdit())
                self.GitHubTokenLineEdit.setText(get_github_token())
                self.GitHubTokenLineEdit.setToolTip(t("settings.connection.github_token_tooltip"))
                self.GitHubTokenLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
                self.GitHubTokenLineEdit.editingFinished.connect(self.update_github_token)

                # Info button for GitHub Token
                self.GitHubTokenInfoButton = gt.add(QPushButton())
                self.GitHubTokenInfoButton.setIcon(self.icons.wiki)
                self.GitHubTokenInfoButton.setFixedSize(QSize(28, 28))
                self.GitHubTokenInfoButton.setToolTip(t("settings.connection.github_token_info_button_tooltip"))
                self.GitHubTokenInfoButton.clicked.connect(self.open_github_token_docs)

        # Proxy Settings
        with self.group("settings.connection.proxy_settings") as grp:
            grp.add_checkbox(
                "settings.connection.use_custom_tls_certificates",
                default=get_use_custom_tls_certificates(),
                setter=set_use_custom_tls_certificates,
            )

            # Proxy Type
            self.ProxyTypeComboBox = grp.add(QComboBox(), "settings.connection.proxy_type")
            self.ProxyTypeComboBox.addItems(proxy_types.keys())
            self.ProxyTypeComboBox.setToolTip(t("settings.connection.proxy_type_tooltip"))
            self.ProxyTypeComboBox.setCurrentIndex(get_proxy_type())
            self.ProxyTypeComboBox.activated[int].connect(self.change_proxy_type)

            # Proxy URL
            with grp.hgroup("settings.connection.proxy_ip") as url:
                # Host
                self.ProxyHostLineEdit = url.add(QLineEdit())
                self.ProxyHostLineEdit.setText(get_proxy_host())
                self.ProxyHostLineEdit.setToolTip(t("settings.connection.proxy_host_tooltip"))
                self.ProxyHostLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

                rx = QRegularExpression(
                    r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
                )

                self.host_validator = QtGui.QRegularExpressionValidator(rx, self)
                self.ProxyHostLineEdit.setValidator(self.host_validator)
                self.ProxyHostLineEdit.editingFinished.connect(self.update_proxy_host)

                url.add_label(" : ")

                # Port
                self.ProxyPortLineEdit = url.add(QLineEdit())
                self.ProxyPortLineEdit.setText(get_proxy_port())
                self.ProxyPortLineEdit.setToolTip(t("settings.connection.proxy_port_tooltip"))
                self.ProxyPortLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

                rx = QRegularExpression(r"\d{2,5}")

                self.port_validator = QtGui.QRegularExpressionValidator(rx, self)
                self.ProxyPortLineEdit.setValidator(self.port_validator)
                self.ProxyPortLineEdit.editingFinished.connect(self.update_proxy_port)

            # Proxy authentication
            # User
            self.ProxyUserLineEdit = grp.add(QLineEdit(), "settings.connection.proxy_user")
            self.ProxyUserLineEdit.setText(get_proxy_user())
            self.ProxyUserLineEdit.setToolTip(t("settings.connection.proxy_user_tooltip"))
            self.ProxyUserLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.ProxyUserLineEdit.editingFinished.connect(self.update_proxy_user)

            # Password
            self.ProxyPasswordLineEdit = grp.add(QLineEdit(), "settings.connection.proxy_password")
            self.ProxyPasswordLineEdit.setText(get_proxy_password())
            self.ProxyPasswordLineEdit.setToolTip(t("settings.connection.proxy_password_tooltip"))
            self.ProxyPasswordLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.ProxyPasswordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.ProxyPasswordLineEdit.editingFinished.connect(self.update_proxy_password)

    def change_proxy_type(self, index: int):
        proxy_type = self.ProxyTypeComboBox.itemText(index)
        set_proxy_type(proxy_type)

    def update_proxy_host(self):
        host = self.ProxyHostLineEdit.text()
        set_proxy_host(host)

    def update_proxy_port(self):
        port = self.ProxyPortLineEdit.text()
        set_proxy_port(port)

    def update_proxy_user(self):
        user = self.ProxyUserLineEdit.text()
        set_proxy_user(user)

    def update_proxy_password(self):
        password = self.ProxyPasswordLineEdit.text()
        set_proxy_password(password)

    def update_user_id(self):
        user_id = self.UserIDLineEdit.text()
        set_user_id(user_id)

    def update_github_token(self):
        token = self.GitHubTokenLineEdit.text()
        stored_in_keyring = set_github_token(token)

        # Show popup if token was saved but had to fall back to settings file
        if token and not stored_in_keyring:
            Popup.warning(
                message=t("settings.connection.keyring_unavailable_message"),
                buttons=Popup.Button.info(),
                parent=self.launcher,
            )

    def open_github_token_docs(self):
        QtGui.QDesktopServices.openUrl("https://Victor-IX.github.io/Blender-Launcher-V2/github_token/")
