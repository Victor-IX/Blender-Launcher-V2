from __future__ import annotations

from typing import TYPE_CHECKING

from i18n import t
from modules.settings import (
    downloads_pages,
    get_default_downloads_page,
    get_default_library_page,
    get_default_tab,
    get_dpi_scale_factor,
    get_enable_download_notifications,
    get_enable_new_builds_notifications,
    get_make_error_popup,
    get_sync_library_and_downloads_pages,
    get_use_system_titlebar,
    library_pages,
    set_default_downloads_page,
    set_default_library_page,
    set_default_tab,
    set_dpi_scale_factor,
    set_enable_download_notifications,
    set_enable_new_builds_notifications,
    set_make_error_notifications,
    set_sync_library_and_downloads_pages,
    set_use_system_titlebar,
    tabs,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)
from utils.dpi import DPI_OVERRIDDEN
from widgets.settings_form_widget import SettingsFormWidget

from .settings_group import SettingsGroup

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class AppearanceTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Windows
        self.window_settings = SettingsGroup(t("settings.appearance.window_related"), parent=self)

        # Use System Title Bar
        self.UseSystemTitleBar = QCheckBox()
        self.UseSystemTitleBar.setText(t("settings.appearance.use_system_titlebar"))
        self.UseSystemTitleBar.setToolTip(t("settings.appearance.use_system_titlebar_tooltip"))
        self.UseSystemTitleBar.setChecked(get_use_system_titlebar())
        self.UseSystemTitleBar.clicked.connect(self.toggle_system_titlebar)

        # DPI Scale Factor
        self.DpiScaleFactorSpinBox = QDoubleSpinBox()
        self.DpiScaleFactorSpinBox.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        dpi_scale_label_text = "settings.appearance.dpi_scale_factor"
        if DPI_OVERRIDDEN:
            dpi_scale_label_text = "settings.appearance.dpi_scale_factor_overridden"
            self.DpiScaleFactorSpinBox.setEnabled(False)

        self.DpiScaleFactorLabel = QLabel(t(dpi_scale_label_text))
        self.DpiScaleFactorSpinBox.setToolTip(t("settings.appearance.dpi_scale_factor_tooltip"))
        self.DpiScaleFactorSpinBox.setRange(0.25, 10.0)
        self.DpiScaleFactorSpinBox.setSingleStep(0.05)
        self.DpiScaleFactorSpinBox.setValue(get_dpi_scale_factor())
        self.DpiScaleFactorSpinBox.valueChanged.connect(self.set_dpi_scale_factor)

        self.window_layout = QGridLayout()
        self.window_layout.addWidget(self.UseSystemTitleBar, 0, 0, 1, 2)
        self.window_layout.addWidget(self.DpiScaleFactorSpinBox, 1, 0)
        self.window_layout.addWidget(self.DpiScaleFactorLabel, 1, 1)
        self.window_layout.setColumnStretch(1, 1)

        self.window_settings.setLayout(self.window_layout)

        # Notifications
        self.notification_settings = SettingsGroup(t("settings.appearance.notifications.label"), parent=self)

        self.EnableNewBuildsNotifications = QCheckBox()
        self.EnableNewBuildsNotifications.setText(t("settings.appearance.notifications.new_builds"))
        self.EnableNewBuildsNotifications.setToolTip(t("settings.appearance.notifications.new_builds_tooltip"))
        self.EnableNewBuildsNotifications.clicked.connect(self.toggle_enable_new_builds_notifications)
        self.EnableNewBuildsNotifications.setChecked(get_enable_new_builds_notifications())

        self.EnableDownloadNotifications = QCheckBox()
        self.EnableDownloadNotifications.setText(t("settings.appearance.notifications.finished_downloading"))
        self.EnableDownloadNotifications.setToolTip(t("settings.appearance.notifications.finished_downloading_tooltip"))
        self.EnableDownloadNotifications.clicked.connect(self.toggle_enable_download_notifications)
        self.EnableDownloadNotifications.setChecked(get_enable_download_notifications())

        self.EnableErrorNotifications = QCheckBox()
        self.EnableErrorNotifications.setText(t("settings.appearance.notifications.errors"))
        self.EnableErrorNotifications.setToolTip(t("settings.appearance.notifications.errors_tooltip"))
        self.EnableErrorNotifications.clicked.connect(self.toggle_enable_error_notifications)
        self.EnableErrorNotifications.setChecked(get_make_error_popup())

        self.notification_layout = QVBoxLayout()
        self.notification_layout.addWidget(self.EnableNewBuildsNotifications)
        self.notification_layout.addWidget(self.EnableDownloadNotifications)
        self.notification_layout.addWidget(self.EnableErrorNotifications)
        self.notification_settings.setLayout(self.notification_layout)

        # Tabs
        self.tabs_settings = SettingsGroup(t("settings.appearance.tabs.label"), parent=self)

        # Default Tab
        self.DefaultTabComboBox = QComboBox()
        self.DefaultTabComboBox.addItems(tabs.keys())
        self.DefaultTabComboBox.setToolTip(t("settings.appearance.tabs.default_tab_tooltip"))
        self.DefaultTabComboBox.setCurrentIndex(get_default_tab())
        self.DefaultTabComboBox.activated[int].connect(self.change_default_tab)

        # Sync Library and Downloads pages
        self.SyncLibraryAndDownloadsPages = QCheckBox()
        self.SyncLibraryAndDownloadsPages.setText(t("settings.appearance.tabs.sync_library_and_downloads_pages"))
        self.SyncLibraryAndDownloadsPages.setToolTip(
            t("settings.appearance.tabs.sync_library_and_downloads_pages_tooltip")
        )
        self.SyncLibraryAndDownloadsPages.clicked.connect(self.toggle_sync_library_and_downloads_pages)
        self.SyncLibraryAndDownloadsPages.setChecked(get_sync_library_and_downloads_pages())

        # Default Library Page
        self.DefaultLibraryPageComboBox = QComboBox()
        self.DefaultLibraryPageComboBox.addItems(library_pages.keys())
        self.DefaultLibraryPageComboBox.setToolTip(t("settings.appearance.tabs.default_library_page_tooltip"))
        self.DefaultLibraryPageComboBox.setCurrentIndex(get_default_library_page())
        self.DefaultLibraryPageComboBox.activated[int].connect(self.change_default_library_page)

        # Default Downloads Page
        self.DefaultDownloadsPageComboBox = QComboBox()
        self.DefaultDownloadsPageComboBox.addItems(downloads_pages.keys())
        self.DefaultDownloadsPageComboBox.setToolTip(t("settings.appearance.tabs.default_downloads_page_tooltip"))
        self.DefaultDownloadsPageComboBox.setCurrentIndex(get_default_downloads_page())
        self.DefaultDownloadsPageComboBox.activated[int].connect(self.change_default_downloads_page)

        self.tabs_layout = QFormLayout()
        self.tabs_layout.addRow(QLabel(t("settings.appearance.tabs.default_tab"), self), self.DefaultTabComboBox)
        self.tabs_layout.addRow(self.SyncLibraryAndDownloadsPages)
        self.tabs_layout.addRow(
            QLabel(t("settings.appearance.tabs.default_library_page"), self),
            self.DefaultLibraryPageComboBox,
        )
        self.tabs_layout.addRow(
            QLabel(t("settings.appearance.tabs.default_downloads_page"), self),
            self.DefaultDownloadsPageComboBox,
        )
        self.tabs_settings.setLayout(self.tabs_layout)

        # Layout
        self.addRow(self.window_settings)
        self.addRow(self.notification_settings)
        self.addRow(self.tabs_settings)

    def toggle_system_titlebar(self, is_checked):
        set_use_system_titlebar(is_checked)
        self.launcher.update_system_titlebar(is_checked)

    def set_dpi_scale_factor(self, value: float):
        set_dpi_scale_factor(value)

    def change_default_tab(self, index: int):
        tab = self.DefaultTabComboBox.itemText(index)
        set_default_tab(tab)

    def toggle_sync_library_and_downloads_pages(self, is_checked):
        set_sync_library_and_downloads_pages(is_checked)
        self.launcher.toggle_sync_library_and_downloads_pages(is_checked)

        if is_checked:
            index = self.DefaultLibraryPageComboBox.currentIndex()
            self.DefaultDownloadsPageComboBox.setCurrentIndex(index)
            text = self.DefaultLibraryPageComboBox.currentText()
            set_default_downloads_page(text)

    def change_default_library_page(self, index: int):
        page = self.DefaultLibraryPageComboBox.itemText(index)
        set_default_library_page(page)

        if get_sync_library_and_downloads_pages():
            self.DefaultDownloadsPageComboBox.setCurrentIndex(index)
            set_default_downloads_page(page)

    def change_default_downloads_page(self, index: int):
        page = self.DefaultDownloadsPageComboBox.itemText(index)
        set_default_downloads_page(page)

        if get_sync_library_and_downloads_pages():
            self.DefaultLibraryPageComboBox.setCurrentIndex(index)
            set_default_library_page(page)

    def toggle_enable_download_notifications(self, is_checked):
        set_enable_download_notifications(is_checked)

    def toggle_enable_new_builds_notifications(self, is_checked):
        set_enable_new_builds_notifications(is_checked)

    def toggle_enable_error_notifications(self, is_checked):
        set_make_error_notifications(is_checked)
