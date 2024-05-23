from modules.settings import (
    get_proxy_host,
    get_proxy_password,
    get_proxy_port,
    get_proxy_type,
    get_proxy_user,
    get_use_custom_tls_certificates,
    proxy_types,
    set_proxy_host,
    set_proxy_password,
    set_proxy_port,
    set_proxy_type,
    set_proxy_user,
    set_use_custom_tls_certificates,
)
from PyQt5 import QtGui
from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit
from widgets.settings_form_widget import SettingsFormWidget

from .settings_group import SettingsGroup


class ConnectionTabWidget(SettingsFormWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # Proxy Settings
        self.proxy_settings = SettingsGroup("Proxy", parent=self)

        # Custom TLS certificates
        self.UseCustomCertificatesCheckBox = QCheckBox()
        self.UseCustomCertificatesCheckBox.setText("Use Custom TLS Certificates")
        self.UseCustomCertificatesCheckBox.clicked.connect(self.toggle_use_custom_tls_certificates)
        self.UseCustomCertificatesCheckBox.setChecked(get_use_custom_tls_certificates())

        # Proxy Type
        self.ProxyTypeComboBox = QComboBox()
        self.ProxyTypeComboBox.addItems(proxy_types.keys())
        self.ProxyTypeComboBox.setCurrentIndex(get_proxy_type())
        self.ProxyTypeComboBox.activated[str].connect(self.change_proxy_type)

        # Proxy URL
        # Host
        self.ProxyHostLineEdit = QLineEdit()
        self.ProxyHostLineEdit.setText(get_proxy_host())
        self.ProxyHostLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        rx = QRegExp(
            r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        )
        self.host_validator = QtGui.QRegExpValidator(rx, self)
        self.ProxyHostLineEdit.setValidator(self.host_validator)
        self.ProxyHostLineEdit.editingFinished.connect(self.update_proxy_host)

        # Port
        self.ProxyPortLineEdit = QLineEdit()
        self.ProxyPortLineEdit.setText(get_proxy_port())
        self.ProxyPortLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        rx = QRegExp(r"\d{2,5}")
        self.port_validator = QtGui.QRegExpValidator(rx, self)
        self.ProxyPortLineEdit.setValidator(self.port_validator)
        self.ProxyPortLineEdit.editingFinished.connect(self.update_proxy_port)

        # Proxy authentication
        # User
        self.ProxyUserLineEdit = QLineEdit()
        self.ProxyUserLineEdit.setText(get_proxy_user())
        self.ProxyUserLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.ProxyUserLineEdit.editingFinished.connect(self.update_proxy_user)

        # Password
        self.ProxyPasswordLineEdit = QLineEdit()
        self.ProxyPasswordLineEdit.setText(get_proxy_password())
        self.ProxyPasswordLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.ProxyPasswordLineEdit.setEchoMode(QLineEdit.Password)
        self.ProxyPasswordLineEdit.editingFinished.connect(self.update_proxy_password)

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

        self.proxy_settings.setLayout(layout)
        self.addRow(self.proxy_settings)

    def toggle_use_custom_tls_certificates(self, is_checked):
        set_use_custom_tls_certificates(is_checked)

    def change_proxy_type(self, proxy_type):
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
