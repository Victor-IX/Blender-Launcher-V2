from __future__ import annotations

from typing import TYPE_CHECKING

import webbrowser

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
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from widgets.settings_form_widget import SettingsFormWidget
from windows.popup_window import PopupIcon, PopupWindow

from .settings_group import SettingsGroup

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class ConnectionTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Get icons
        self.icons = Icons.get()

        # Proxy Settings
        self.proxy_settings = SettingsGroup("Proxy", parent=self)

        # Custom TLS certificates
        self.UseCustomCertificatesCheckBox = QCheckBox()
        self.UseCustomCertificatesCheckBox.setText("Use Custom TLS Certificates")
        self.UseCustomCertificatesCheckBox.setToolTip(
            "Use custom TLS certificates for the connection\
            \nDEFAULT: False"
        )
        self.UseCustomCertificatesCheckBox.clicked.connect(self.toggle_use_custom_tls_certificates)
        self.UseCustomCertificatesCheckBox.setChecked(get_use_custom_tls_certificates())

        # Proxy Type
        self.ProxyTypeComboBox = QComboBox()
        self.ProxyTypeComboBox.addItems(proxy_types.keys())
        self.ProxyTypeComboBox.setToolTip(
            "The type of proxy to use for the connection\
            \nDEFAULT: None"
        )
        self.ProxyTypeComboBox.setCurrentIndex(get_proxy_type())
        self.ProxyTypeComboBox.activated[int].connect(self.change_proxy_type)

        # Proxy URL
        # Host
        self.ProxyHostLineEdit = QLineEdit()
        self.ProxyHostLineEdit.setText(get_proxy_host())
        self.ProxyHostLineEdit.setToolTip(
            "The IP address of the proxy server\
            \nDEFAULT: 255.255.255.255"
        )
        self.ProxyHostLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        rx = QRegularExpression(
            r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        )

        self.host_validator = QtGui.QRegularExpressionValidator(rx, self)
        self.ProxyHostLineEdit.setValidator(self.host_validator)
        self.ProxyHostLineEdit.editingFinished.connect(self.update_proxy_host)

        # Port
        self.ProxyPortLineEdit = QLineEdit()
        self.ProxyPortLineEdit.setText(get_proxy_port())
        self.ProxyPortLineEdit.setToolTip(
            "The port number of the proxy server\
            \nDEFAULT: 9999"
        )
        self.ProxyPortLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        rx = QRegularExpression(r"\d{2,5}")

        self.port_validator = QtGui.QRegularExpressionValidator(rx, self)
        self.ProxyPortLineEdit.setValidator(self.port_validator)
        self.ProxyPortLineEdit.editingFinished.connect(self.update_proxy_port)

        # Proxy authentication
        # User
        self.ProxyUserLineEdit = QLineEdit()
        self.ProxyUserLineEdit.setText(get_proxy_user())
        self.ProxyUserLineEdit.setToolTip("The username to authenticate with the proxy server")
        self.ProxyUserLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.ProxyUserLineEdit.editingFinished.connect(self.update_proxy_user)

        # Password
        self.ProxyPasswordLineEdit = QLineEdit()
        self.ProxyPasswordLineEdit.setText(get_proxy_password())
        self.ProxyPasswordLineEdit.setToolTip("The password to authenticate with the proxy server")
        self.ProxyPasswordLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.ProxyPasswordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ProxyPasswordLineEdit.editingFinished.connect(self.update_proxy_password)

        # Connection Authentication
        self.connection_authentication_settings = SettingsGroup("Connection Authentication", parent=self)

        # User ID
        self.UserIDLabel = QLabel("User ID")
        self.UserIDLineEdit = QLineEdit()
        self.UserIDLineEdit.setText(get_user_id())
        self.UserIDLineEdit.setToolTip(
            "The user ID to authenticate with the Blender website\
            \nDEFAULT: Random UUID\
            \nFORMAT: 8-64 characters (a-z, A-Z, 0-9, -)"
        )

        rx = QRegularExpression(r"^[a-zA-Z0-9-]{8,64}$")

        self.user_id_validator = QtGui.QRegularExpressionValidator(rx, self)
        self.UserIDLineEdit.setValidator(self.user_id_validator)
        self.UserIDLineEdit.editingFinished.connect(self.update_user_id)

        # GitHub Token
        self.GitHubTokenLabel = QLabel("GitHub Token")
        self.GitHubTokenLineEdit = QLineEdit()
        self.GitHubTokenLineEdit.setText(get_github_token())
        self.GitHubTokenLineEdit.setToolTip(
            "Optional: GitHub Personal Access Token to avoid rate limiting\n"
            "Useful if you're making many requests to GitHub API\n"
            "Leave empty if not needed"
        )
        self.GitHubTokenLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.GitHubTokenLineEdit.editingFinished.connect(self.update_github_token)

        # Info button for GitHub Token
        self.GitHubTokenInfoButton = QPushButton()
        self.GitHubTokenInfoButton.setIcon(self.icons.wiki)
        self.GitHubTokenInfoButton.setFixedSize(QSize(28, 28))
        self.GitHubTokenInfoButton.setToolTip("Click for GitHub token documentation")
        self.GitHubTokenInfoButton.clicked.connect(self.open_github_token_docs)

        # Layout for token field with info button
        github_token_layout = QHBoxLayout()
        github_token_layout.addWidget(self.GitHubTokenLineEdit)
        github_token_layout.addWidget(self.GitHubTokenInfoButton)

        self.connection_authentication_layout = QGridLayout()
        self.connection_authentication_layout.addWidget(self.UserIDLabel, 0, 0, 1, 1)
        self.connection_authentication_layout.addWidget(self.UserIDLineEdit, 0, 1, 1, 1)
        self.connection_authentication_layout.addWidget(self.GitHubTokenLabel, 1, 0, 1, 1)
        self.connection_authentication_layout.addLayout(github_token_layout, 1, 1, 1, 1)
        self.connection_authentication_settings.setLayout(self.connection_authentication_layout)

        # Layout
        layout = QFormLayout()
        layout.addRow(self.UseCustomCertificatesCheckBox)
        layout.addRow(QLabel("Type", self), self.ProxyTypeComboBox)
        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.ProxyHostLineEdit)
        sub_layout.addWidget(QLabel(" : "))
        sub_layout.addWidget(self.ProxyPortLineEdit)
        layout.addRow(QLabel("IP", self), sub_layout)
        layout.addRow(QLabel("Proxy User", self), self.ProxyUserLineEdit)
        layout.addRow(QLabel("Password", self), self.ProxyPasswordLineEdit)

        self.addRow(self.connection_authentication_settings)

        self.proxy_settings.setLayout(layout)
        self.addRow(self.proxy_settings)

    def toggle_use_custom_tls_certificates(self, is_checked):
        set_use_custom_tls_certificates(is_checked)

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
            PopupWindow(
                title="Keyring Unavailable",
                message=(
                    "Failed to store GitHub token in secure system keyring.\n\n"
                    "The token has been saved to your settings file instead.\n"
                    "This is less secure than keyring storage.\n\n"
                    "Consider installing keyring support for your system."
                ),
                icon=PopupIcon.WARNING,
                info_popup=True,
                parent=self.launcher,
            )

    def open_github_token_docs(self):
        webbrowser.open("https://Victor-IX.github.io/Blender-Launcher-V2/github_token/")
