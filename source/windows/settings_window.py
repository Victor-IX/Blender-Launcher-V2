from i18n import t
from modules.settings import (
    get_check_for_new_builds_automatically,
    get_dpi_scale_factor,
    get_enable_quick_launch_key_seq,
    get_language,
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
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QScrollArea, QTabWidget, QVBoxLayout, QWidget
from widgets.header import WindowHeader
from widgets.settings_window import appearance_tab, blender_builds_tab, connection_tab, general_tab
from widgets.tab_widget import TabWidget
from windows.base_window import BaseWindow
from windows.popup_window import Popup


class SettingsWindow(BaseWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.resize(QSize(700, 800))
        self.setMinimumSize(QSize(500, 600))

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

        self.old_dpi_scale_factor = get_dpi_scale_factor()
        self.old_thread_count = get_worker_thread_count()
        self.old_language = get_language()

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

        # General Tab
        self.GeneralTab = TabWidget(self.TabWidget, "General")
        self.GeneralScrollArea = QScrollArea()
        self.GeneralScrollArea.setWidgetResizable(True)
        self.GeneralScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.GeneralScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.GeneralScrollArea.setFrameShape(QScrollArea.Shape.NoFrame)
        self.GeneralTabWidget = general_tab.GeneralTabWidget(parent=self.launcher)
        self.GeneralScrollArea.setWidget(self.GeneralTabWidget)
        self.GeneralTab.layout().addWidget(self.GeneralScrollArea)

        # Appearance Tab
        self.AppearanceTab = TabWidget(self.TabWidget, "Appearance")
        self.AppearanceScrollArea = QScrollArea()
        self.AppearanceScrollArea.setWidgetResizable(True)
        self.AppearanceScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.AppearanceScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.AppearanceScrollArea.setFrameShape(QScrollArea.Shape.NoFrame)
        self.AppearanceTabWidget = appearance_tab.AppearanceTabWidget(parent=self.launcher)
        self.AppearanceScrollArea.setWidget(self.AppearanceTabWidget)
        self.AppearanceTab.layout().addWidget(self.AppearanceScrollArea)

        # Connection Tab
        self.ConnectionTab = TabWidget(self.TabWidget, "Connection")
        self.ConnectionScrollArea = QScrollArea()
        self.ConnectionScrollArea.setWidgetResizable(True)
        self.ConnectionScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ConnectionScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.ConnectionScrollArea.setFrameShape(QScrollArea.Shape.NoFrame)
        self.ConnectionTabWidget = connection_tab.ConnectionTabWidget(parent=self.launcher)
        self.ConnectionScrollArea.setWidget(self.ConnectionTabWidget)
        self.ConnectionTab.layout().addWidget(self.ConnectionScrollArea)

        # Blender Builds Tab
        self.BlenderBuildsTab = TabWidget(self.TabWidget, "Blender Builds")
        self.BlenderBuildsScrollArea = QScrollArea()
        self.BlenderBuildsScrollArea.setWidgetResizable(True)
        self.BlenderBuildsScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.BlenderBuildsScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.BlenderBuildsScrollArea.setFrameShape(QScrollArea.Shape.NoFrame)
        self.BlenderBuildsTabWidget = blender_builds_tab.BlenderBuildsTabWidget(parent=self.launcher)
        self.BlenderBuildsScrollArea.setWidget(self.BlenderBuildsTabWidget)
        self.BlenderBuildsTab.layout().addWidget(self.BlenderBuildsScrollArea)

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
                self.launcher.setup_global_hotkeys_listener()
            # Stop hotkeys listener
            elif self.launcher.hk_listener is not None:
                self.launcher.hk_listener.stop()
        # Only key sequence was changed
        # Restart hotkeys listener
        elif self.old_quick_launch_key_seq != quick_launch_key_seq and enable_quick_launch_key_seq:
            self.launcher.setup_global_hotkeys_listener()

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
                t("settings.connection.use_custom_tls_certificates")
                + checkdct[self.old_use_custom_tls_certificates]
                + "🠆"
                + checkdct[use_custom_tls_certificates]
            )

        if self.old_proxy_type != proxy_type:
            r_proxy_types = dict(zip(proxy_types.values(), proxy_types.keys(), strict=True))

            pending_to_restart.append(
                f"{t('settings.connection.proxy_type')}: {r_proxy_types[self.old_proxy_type]}🠆{r_proxy_types[proxy_type]}"
            )

        if self.old_proxy_host != proxy_host:
            pending_to_restart.append(f"{t('settings.connection.proxy_host')}: {self.old_proxy_host}🠆{proxy_host}")

        if self.old_proxy_port != proxy_port:
            pending_to_restart.append(f"{t('settings.connection.proxy_port')}: {self.old_proxy_port}🠆{proxy_port}")

        if self.old_proxy_user != proxy_user:
            pending_to_restart.append(f"{t('settings.connection.proxy_user')}: {self.old_proxy_user}🠆{proxy_user}")

        if self.old_proxy_password != proxy_password:
            pending_to_restart.append(t("settings.connection.proxy_password"))

        if self.old_user_id != user_id:
            pending_to_restart.append(f"{t('settings.connection.user_id')}: {self.old_user_id}🠆{user_id}")

        """Update build check frequency"""
        check_for_new_builds_automatically = get_check_for_new_builds_automatically()
        new_builds_check_frequency = get_new_builds_check_frequency()

        # Restart scraper if any of the build check settings changed
        if (
            self.old_check_for_new_builds_automatically != check_for_new_builds_automatically
            or self.old_new_builds_check_frequency != new_builds_check_frequency
        ):
            self.launcher.draw_library(clear=True)

        """Update DPI Scale Factor"""
        dpi_scale_factor = get_dpi_scale_factor()

        if self.old_dpi_scale_factor != dpi_scale_factor:
            pending_to_restart.append(
                f"{t('settings.appearance.dpi_scale_factor')}: {self.old_dpi_scale_factor:.2f}🠆{dpi_scale_factor:.2f}",
            )

        """Update worker thread count"""
        worker_thread_count = get_worker_thread_count()

        if self.old_thread_count != worker_thread_count:
            pending_to_restart.append(f"{t('settings.general.app.worker_count')}: {self.old_thread_count}🠆{worker_thread_count}")

        """Update language"""
        language = get_language()

        if self.old_language != language:
            pending_to_restart.append(f"{t('settings.general.app.language')}: {self.old_language}🠆{language}")

        return pending_to_restart

    def show_dlg_restart_bl(self, pending: list[str]):
        pending_to_restart = "".join(f"\n- {s}" for s in pending)

        self.dlg = Popup.warning(
            parent=self.launcher,
            message=t("msg.popup.apply_the_following", pending=pending_to_restart),
            buttons=[Popup.Button.RESTART_NOW, Popup.Button.LATER],
        )
        self.dlg.accepted.connect(self.restart_app)
        self.dlg.cancelled.connect(self.attempt_close)
        self.close_warning_ignored = True  # if the user tries to restart then the close event won't trigger

    def restart_app(self):
        self.launcher.restart_app()

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
            self.launcher.settings_window = None
            self.launcher.update_visible_lists()
            event.accept()
