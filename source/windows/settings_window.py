from modules.settings import (
    get_check_for_new_builds_automatically,
    get_enable_high_dpi_scaling,
    get_enable_quick_launch_key_seq,
    get_new_builds_check_frequency,
    get_proxy_host,
    get_proxy_password,
    get_proxy_port,
    get_proxy_type,
    get_proxy_user,
    get_quick_launch_key_seq,
    get_use_custom_tls_certificates,
    get_user_id,
    get_worker_thread_count,
    proxy_types,
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QSizePolicy, QTabWidget, QVBoxLayout, QWidget
from widgets.header import WindowHeader
from widgets.settings_window import appearance_tab, blender_builds_tab, connection_tab, general_tab
from widgets.tab_widget import TabWidget
from windows.base_window import BaseWindow
from windows.dialog_window import DialogWindow


class SettingsWindow(BaseWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        sizePolicy = QSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.MinimumExpanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(480, 777))
        self.CentralWidget = QWidget(self)
        self.CentralLayout = QVBoxLayout(self.CentralWidget)
        self.CentralLayout.setContentsMargins(1, 1, 1, 1)
        self.setCentralWidget(self.CentralWidget)
        self.setWindowTitle("Settings")

        # Global scope for breaking settings
        self.old_enable_quick_launch_key_seq = get_enable_quick_launch_key_seq()
        self.old_quick_launch_key_seq = get_quick_launch_key_seq()

        self.old_use_custom_tls_certificates = get_use_custom_tls_certificates()
        self.old_proxy_type = get_proxy_type()
        self.old_proxy_host = get_proxy_host()
        self.old_proxy_port = get_proxy_port()
        self.old_proxy_user = get_proxy_user()
        self.old_proxy_password = get_proxy_password()
        self.old_user_id = get_user_id()

        self.old_check_for_new_builds_automatically = get_check_for_new_builds_automatically()
        self.old_new_builds_check_frequency = get_new_builds_check_frequency()

        self.old_enable_high_dpi_scaling = get_enable_high_dpi_scaling()
        self.old_thread_count = get_worker_thread_count()

        # Header layout
        self.header = WindowHeader(self, "Settings", use_minimize=False)
        self.header.close_signal.connect(self.attempt_close)
        self.CentralLayout.addWidget(self.header)
        self.update_system_titlebar(self.using_system_bar)

        self.close_warning_ignored = False

        # Tab Layout
        self.TabWidget = QTabWidget()
        self.TabWidget.setProperty("Center", True)
        self.CentralLayout.addWidget(self.TabWidget)

        self.GeneralTab = TabWidget(self.TabWidget, "General")
        self.GeneralTabWidget = general_tab.GeneralTabWidget(parent=self.parent)
        self.GeneralTab.layout().addWidget(self.GeneralTabWidget)

        self.AppearanceTab = TabWidget(self.TabWidget, "Appearance")
        self.AppearanceTabWidget = appearance_tab.AppearanceTabWidget(parent=self.parent)
        self.AppearanceTab.layout().addWidget(self.AppearanceTabWidget)

        self.ConnectionTab = TabWidget(self.TabWidget, "Connection")
        self.ConnectionTabWidget = connection_tab.ConnectionTabWidget(parent=self.parent)
        self.ConnectionTab.layout().addWidget(self.ConnectionTabWidget)

        self.BlenderBuildsTab = TabWidget(self.TabWidget, "Blender Builds")
        self.BlenderBuildsTabWidget = blender_builds_tab.BlenderBuildsTabWidget(parent=self.parent)
        self.BlenderBuildsTab.layout().addWidget(self.BlenderBuildsTabWidget)

        self.resize(self.sizeHint())
        self.show()

    def get_unfinished_business(self) -> list[str]:
        pending_to_restart = []
        checkdct = {True: "ON", False: "OFF"}

        """Update quick launch key"""
        enable_quick_launch_key_seq = get_enable_quick_launch_key_seq()
        quick_launch_key_seq = get_quick_launch_key_seq()
        # Quick launch was enabled or disabled
        if self.old_enable_quick_launch_key_seq != enable_quick_launch_key_seq:
            # Restart hotkeys listener
            if enable_quick_launch_key_seq is True:
                self.parent.setup_global_hotkeys_listener()
            # Stop hotkeys listener
            elif self.parent.hk_listener is not None:
                self.parent.hk_listener.stop()
        # Only key sequence was changed
        # Restart hotkeys listener
        elif self.old_quick_launch_key_seq != quick_launch_key_seq and enable_quick_launch_key_seq:
            self.parent.setup_global_hotkeys_listener()

        """Update connection"""
        use_custom_tls_certificates = get_use_custom_tls_certificates()
        proxy_type = get_proxy_type()
        proxy_host = get_proxy_host()
        proxy_port = get_proxy_port()
        proxy_user = get_proxy_user()
        proxy_password = get_proxy_password()
        user_id = get_user_id()

        # Restart app if any of the connection settings changed
        if self.old_use_custom_tls_certificates != use_custom_tls_certificates:
            pending_to_restart.append(
                "Use Custom TLS Certificates: "
                + checkdct[self.old_use_custom_tls_certificates]
                + "🠆"
                + checkdct[use_custom_tls_certificates]
            )

        if self.old_proxy_type != proxy_type:
            r_proxy_types = dict(zip(proxy_types.values(), proxy_types.keys()))

            pending_to_restart.append(f"Proxy Type: {r_proxy_types[self.old_proxy_type]}🠆{r_proxy_types[proxy_type]}")

        if self.old_proxy_host != proxy_host:
            pending_to_restart.append(f"Proxy Host: {self.old_proxy_host}🠆{proxy_host}")

        if self.old_proxy_port != proxy_port:
            pending_to_restart.append(f"Proxy Port: {self.old_proxy_port}🠆{proxy_port}")

        if self.old_proxy_user != proxy_user:
            pending_to_restart.append(f"Proxy User: {self.old_proxy_user}🠆{proxy_user}")

        if self.old_proxy_password != proxy_password:
            pending_to_restart.append("Proxy Password")

        if self.old_user_id != user_id:
            pending_to_restart.append(f"User ID: {self.old_user_id}🠆{user_id}")

        """Update build check frequency"""
        check_for_new_builds_automatically = get_check_for_new_builds_automatically()
        new_builds_check_frequency = get_new_builds_check_frequency()

        # Restart scraper if any of the build check settings changed
        if (
            self.old_check_for_new_builds_automatically != check_for_new_builds_automatically
            or self.old_new_builds_check_frequency != new_builds_check_frequency
        ):
            self.parent.draw_library(clear=True)

        """Update high DPI scaling"""
        enable_high_dpi_scaling = get_enable_high_dpi_scaling()

        if self.old_enable_high_dpi_scaling != enable_high_dpi_scaling:
            pending_to_restart.append(
                "High DPI Scaling: "
                + checkdct[self.old_enable_high_dpi_scaling]
                + "🠆"
                + checkdct[enable_high_dpi_scaling],
            )

        """Update worker thread count"""
        worker_thread_count = get_worker_thread_count()

        if self.old_thread_count != worker_thread_count:
            pending_to_restart.append(f"Worker Threads: {self.old_thread_count}🠆{worker_thread_count}")

        return pending_to_restart

    def show_dlg_restart_bl(self, pending: list[str]):
        pending_to_restart = ""

        for s in pending:
            pending_to_restart += "<br>- " + s

        self.dlg = DialogWindow(
            parent=self.parent,
            title="Warning",
            text=f"Restart Blender Launcher in<br> \
                  order to apply following settings:{pending_to_restart}",
            accept_text="Restart Now",
            cancel_text="Ignore",
        )
        self.dlg.accepted.connect(self.restart_app)
        self.dlg.cancelled.connect(self.attempt_close)
        self.close_warning_ignored = True  # if the user tries to restart then the close event won't trigger

    def restart_app(self):
        self.parent.restart_app()

    def update_system_titlebar(self, b: bool):
        self.header.setHidden(b)

    def attempt_close(self):
        self.close()

    def closeEvent(self, event):
        unfinished_business = self.get_unfinished_business()
        if unfinished_business and not self.close_warning_ignored:
            self.show_dlg_restart_bl(unfinished_business)
            event.ignore()
        else:
            self.parent.settings_window = None
            self.parent.update_visible_lists()
            event.accept()
