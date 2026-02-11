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
    QComboBox,
)
from utils.dpi import DPI_OVERRIDDEN
from widgets.settings_form_widget import SettingsFormWidget

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class AppearanceTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Windows
        with self.group("settings.appearance.window_related") as grp:
            # Use System Title Bar
            grp.add_checkbox(
                "settings.appearance.use_system_titlebar",
                default=get_use_system_titlebar(),
                setter=self.toggle_system_titlebar,
            )

            # DPI Scale Factor
            spin = grp.add_double_spin(
                "settings.appearance.dpi_scale_factor"
                if not DPI_OVERRIDDEN
                else "settings.appearance.dpi_scale_factor_overridden",
                default=get_dpi_scale_factor(),
                setter=set_dpi_scale_factor,
                min_=0.25,
                max_=10.0,
                step=0.05,
            )
            spin.setEnabled(not DPI_OVERRIDDEN)

        # Notifications
        with self.group("settings.appearance.notifications.label") as grp:
            grp.add_checkbox(
                "settings.appearance.notifications.new_builds",
                default=get_enable_new_builds_notifications(),
                setter=set_enable_new_builds_notifications,
            )
            grp.add_checkbox(
                "settings.appearance.notifications.finished_downloading",
                default=get_enable_download_notifications(),
                setter=set_enable_download_notifications,
            )
            grp.add_checkbox(
                "settings.appearance.notifications.errors",
                default=get_make_error_popup(),
                setter=set_make_error_notifications,
            )

        # Tabs
        with self.group("settings.appearance.tabs.label") as grp:
            self.DefaultTabComboBox = grp.add(QComboBox(), "settings.appearance.tabs.default_tab")
            self.DefaultTabComboBox.addItems(tabs.keys())
            self.DefaultTabComboBox.setToolTip(t("settings.appearance.tabs.default_tab_tooltip"))
            self.DefaultTabComboBox.setCurrentIndex(get_default_tab())
            self.DefaultTabComboBox.activated[int].connect(self.change_default_tab)

            # Sync Library and Downloads pages
            grp.add_checkbox(
                "settings.appearance.tabs.sync_library_and_downloads_pages",
                default=get_sync_library_and_downloads_pages(),
                setter=self.toggle_sync_library_and_downloads_pages,
            )

            # Default Library Page
            self.DefaultLibraryPageComboBox = grp.add(QComboBox(), "settings.appearance.tabs.default_library_page")
            self.DefaultLibraryPageComboBox.addItems(library_pages.keys())
            self.DefaultLibraryPageComboBox.setToolTip(t("settings.appearance.tabs.default_library_page_tooltip"))
            self.DefaultLibraryPageComboBox.setCurrentIndex(get_default_library_page())
            self.DefaultLibraryPageComboBox.activated[int].connect(self.change_default_library_page)

            # Default Downloads Page
            self.DefaultDownloadsPageComboBox = grp.add(QComboBox(), "settings.appearance.tabs.default_downloads_page")
            self.DefaultDownloadsPageComboBox.addItems(downloads_pages.keys())
            self.DefaultDownloadsPageComboBox.setToolTip(t("settings.appearance.tabs.default_downloads_page_tooltip"))
            self.DefaultDownloadsPageComboBox.setCurrentIndex(get_default_downloads_page())
            self.DefaultDownloadsPageComboBox.activated[int].connect(self.change_default_downloads_page)

    def toggle_system_titlebar(self, is_checked):
        set_use_system_titlebar(is_checked)
        self.launcher.update_system_titlebar(is_checked)

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
