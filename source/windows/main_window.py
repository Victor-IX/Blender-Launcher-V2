from __future__ import annotations

import logging
import os
import shlex
import shutil
import sys
import webbrowser
import threading
from datetime import datetime
from enum import Enum
from functools import partial
from pathlib import Path
from time import localtime, mktime, strftime
from typing import TYPE_CHECKING

from items.base_list_widget_item import BaseListWidgetItem
from modules._platform import _popen, get_cwd, get_default_library_folder, get_launcher_name, get_platform, is_frozen
from modules._resources_rc import RESOURCES_AVAILABLE
from modules.bl_instance_handler import BLInstanceHandler
from modules.connection_manager import ConnectionManager
from modules.enums import MessageType
from modules.settings import (
    create_library_folders,
    get_check_for_new_builds_on_startup,
    get_default_downloads_page,
    get_default_library_page,
    get_default_tab,
    get_dont_show_resource_warning,
    get_enable_download_notifications,
    get_enable_new_builds_notifications,
    get_enable_quick_launch_key_seq,
    get_first_time_setup_seen,
    get_last_time_checked_utc,
    get_launch_minimized_to_tray,
    get_library_folder,
    get_make_error_popup,
    get_proxy_type,
    get_quick_launch_key_seq,
    get_scrape_bfa_builds,
    get_scrape_daily_builds,
    get_scrape_experimental_builds,
    get_scrape_stable_builds,
    get_show_bfa_builds,
    get_show_daily_builds,
    get_show_experimental_and_patch_builds,
    get_show_stable_builds,
    get_show_tray_icon,
    get_sync_library_and_downloads_pages,
    get_tray_icon_notified,
    get_use_pre_release_builds,
    get_use_system_titlebar,
    get_worker_thread_count,
    get_check_for_new_builds_automatically,
    get_new_builds_check_frequency,
    is_library_folder_valid,
    set_dont_show_resource_warning,
    set_last_time_checked_utc,
    set_library_folder,
    set_tray_icon_notified,
)
from modules.string_utils import patch_note_cleaner
from modules.tasks import TaskQueue, TaskWorker
from PySide6.QtCore import QSize, Qt, Signal, Slot, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from semver import Version
from threads.library_drawer import DrawLibraryTask
from threads.remover import RemovalTask
from threads.scraper import Scraper
from widgets.base_menu_widget import BaseMenuWidget
from widgets.base_page_widget import BasePageWidget
from widgets.base_tool_box_widget import BaseToolBoxWidget
from widgets.datetime_widget import DATETIME_FORMAT
from widgets.download_widget import DownloadState, DownloadWidget
from widgets.foreign_build_widget import UnrecoBuildWidget
from widgets.header import WHeaderButton, WindowHeader
from widgets.library_widget import LibraryWidget
from widgets.navigation import SidebarWidget
from windows.base_window import BaseWindow
from windows.file_dialog_window import FileDialogWindow
from windows.onboarding_window import OnboardingWindow
from windows.popup_window import PopupIcon, PopupWindow
from windows.settings_window import SettingsWindow

try:
    from pynput import keyboard

    HOTKEYS_AVAILABLE = True
except Exception as e:
    logging.exception(f"Error importing pynput: {e}\nGlobal hotkeys not supported.")
    HOTKEYS_AVAILABLE = False


if TYPE_CHECKING:
    from modules.build_info import BuildInfo
    from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent
    from widgets.base_build_widget import BaseBuildWidget
    from widgets.base_list_widget import BaseListWidget

# if get_platform() == "Windows":
#     from PySide6.QtWinExtras import QWinThumbnailToolBar, QWinThumbnailToolButton

logger = logging.getLogger()


class AppState(Enum):
    IDLE = 1
    CHECKINGBUILDS = 2


class BlenderLauncher(BaseWindow):
    show_signal = Signal()
    close_signal = Signal()
    quit_signal = Signal()
    quick_launch_fail_signal = Signal()
    scraper_finished_signal = Signal()

    def __init__(
        self,
        app: QApplication,
        version: Version,
        offline: bool = False,
        build_cache: bool = False,
        force_first_time: bool = False,
    ):
        super().__init__(app=app, version=version)
        self.resize(800, 700)
        self.setMinimumSize(QSize(640, 480))
        self.setMaximumWidth(1250)
        widget = QWidget(self)
        self.CentralLayout = QVBoxLayout(widget)
        self.CentralLayout.setContentsMargins(1, 1, 1, 1)
        self.setCentralWidget(widget)
        self.setAcceptDrops(True)

        # Server
        self.instance_handler = BLInstanceHandler(self)
        self.instance_handler.show_launcher.connect(self._show)

        self.quick_launch_fail_signal.connect(self.quick_launch_fail)

        # task queue
        self.task_queue = TaskQueue(
            worker_count=get_worker_thread_count(),
            parent=self,
            on_spawn=self.on_worker_creation,
        )
        self.task_queue.start()
        self.quit_signal.connect(self.task_queue.fullstop)

        # Global scope
        self.app = app
        self.version: Version = version
        self.offline = offline
        self.build_cache = build_cache
        self.favorite: LibraryWidget | None = None
        self.status = "Unknown"
        self.is_force_check_on = False
        self.app_state = AppState.IDLE
        self.cashed_builds = []
        self.notification_pool = []
        self.windows = [self]
        self.timer = None
        self.started = True
        self.latest_tag = ""
        self.new_downloads = False
        self.platform = get_platform()
        self.settings_window = None
        self.hk_listener = None
        self.last_time_checked = get_last_time_checked_utc()

        if self.platform == "macOS":
            self.app.aboutToQuit.connect(self.quit_)

        # Setup window
        self.setWindowTitle("Blender Launcher")
        self.app.setWindowIcon(self.icons.taskbar)

        # Setup scraper
        self.scraper = Scraper(self, self.cm, self.build_cache)
        self.scraper.links.connect(self.draw_to_downloads)
        self.scraper.error.connect(self.connection_error)
        self.scraper.stable_error.connect(self.scraper_error)
        self.scraper.new_bl_version.connect(self.set_version)
        self.scraper.finished.connect(self.scraper_finished)

        # Vesrion Update
        self.pre_release_build = get_use_pre_release_builds

        if not RESOURCES_AVAILABLE and not get_dont_show_resource_warning():
            dlg = PopupWindow(
                parent=self,
                title="Error",
                message="Resources failed to load! The launcher will still work,<br> \
                but the style will be broken.",
                icon=PopupIcon.WARNING,
                buttons=["OK", "Don't Show Again"],
            )
            dlg.cancelled.connect(set_dont_show_resource_warning)

        if (not get_first_time_setup_seen()) or force_first_time:
            self.onboarding_window = OnboardingWindow(version, self)
            self.onboarding_window.accepted.connect(lambda: self.draw())
            self.onboarding_window.cancelled.connect(self.app.quit)
            self.onboarding_window.show()
            return

        # Double-check library folder
        # This is necessary because sometimes the user can move/update the library_folder
        # into an unknown state without them realizing. If we show the program without a
        # valid library folder, then many things will break.
        if is_library_folder_valid() is False:
            self.dlg = PopupWindow(
                parent=self,
                title="Setup",
                message="Choose where Blender<br>builds will be stored",
                buttons=["Continue"],
                icon=PopupIcon.INFO,
            )
            self.dlg.accepted.connect(self.prompt_library_folder)
            return

        create_library_folders(get_library_folder())
        self.draw()

    def prompt_library_folder(self):
        library_folder = get_default_library_folder().as_posix()
        new_library_folder = FileDialogWindow().get_directory(self, "Select Library Folder", library_folder)

        if new_library_folder:
            self.set_library_folder(Path(new_library_folder))
        else:
            self.app.quit()

    def set_library_folder(self, folder: Path, relative: bool | None = None):
        """
        Sets the library folder.
        if relative is None and the folder *can* be relative, it will ask the user if it should use a relative path.
        if relative is bool, it will / will not set the library folder as relative.
        """

        if folder.is_relative_to(get_cwd()):
            if relative is None:
                self.dlg = PopupWindow(
                    parent=self,
                    title="Setup",
                    message="The selected path is relative to the executable's path.<br>\
                        Would you like to save it as relative?<br>\
                        This is useful if the folder may move.",
                    buttons=["Yes", "No"],
                    icon=PopupIcon.NONE,
                )
                self.dlg.accepted.connect(lambda: self.set_library_folder(folder, True))
                self.dlg.cancelled.connect(lambda: self.set_library_folder(folder, False))
                return

            if relative:
                folder = folder.relative_to(get_cwd())

        if set_library_folder(str(folder)) is True:
            self.draw(True)
        else:
            self.dlg = PopupWindow(
                parent=self,
                title="Warning",
                message="Selected folder is not valid or<br>\
                doesn't have write permissions!",
                buttons=["Retry"],
            )
            self.dlg.accepted.connect(self.prompt_library_folder)

    def update_system_titlebar(self, b: bool):
        for window in self.windows:
            window.set_system_titlebar(b)
            if window is not self:
                window.update_system_titlebar(b)
        self.header.setHidden(b)
        self.corner_settings_widget.setHidden(not b)

    def toggle_sync_library_and_downloads_pages(self, is_sync):
        if is_sync:
            self.LibraryToolBox.tab_changed.connect(self.DownloadsToolBox.setCurrentIndex)
            self.DownloadsToolBox.tab_changed.connect(self.LibraryToolBox.setCurrentIndex)
        else:
            if self.isSignalConnected(self.LibraryToolBox, "tab_changed()"):
                self.LibraryToolBox.tab_changed.disconnect()

            if self.isSignalConnected(self.DownloadsToolBox, "tab_changed()"):
                self.DownloadsToolBox.tab_changed.disconnect()

    def isSignalConnected(self, obj, name):
        index = obj.metaObject().indexOfMethod(name)
        if index == -1:
            return False
        method = obj.metaObject().method(index)
        return obj.isSignalConnected(method)

    def draw(self, polish=False):
        # Header
        self.CheckUpdatesButton = WHeaderButton(self.icons.update, "", self)
        self.CheckUpdatesButton.setToolTip(
            "Check for new builds online\n"
            "(Hold SHIFT to force check stable and automated builds)"
        )
        self.CheckUpdatesButton.clicked.connect(self.force_check)
        self.CheckUpdatesButton.setProperty("HeaderButton", True)

        self.SettingsButton = WHeaderButton(self.icons.settings, "", self)
        self.SettingsButton.setToolTip("Show settings window")
        self.SettingsButton.clicked.connect(self.show_settings_window)
        self.DocsButton = WHeaderButton(self.icons.wiki, "", self)
        self.DocsButton.setToolTip("Open documentation")
        self.DocsButton.clicked.connect(self.open_docs)

        self.SettingsButton.setProperty("HeaderButton", True)
        self.DocsButton.setProperty("HeaderButton", True)

        self.corner_settings = QPushButton(self.icons.settings, "", self)
        self.corner_settings.clicked.connect(self.show_settings_window)
        self.corner_docs = QPushButton(self.icons.wiki, "", self)
        self.corner_docs.clicked.connect(self.open_docs)

        self.corner_settings_widget = QWidget(self)
        # self.corner_settings_widget.setMaximumHeight(25)
        self.corner_settings_widget.setContentsMargins(0, 0, 0, 0)
        self.corner_settings_layout = QHBoxLayout(self.corner_settings_widget)
        self.corner_settings_layout.addWidget(self.corner_docs)
        self.corner_settings_layout.addWidget(self.corner_settings)
        self.corner_settings_layout.setContentsMargins(0, 0, 0, 0)
        self.corner_settings_layout.setSpacing(0)

        self.header = WindowHeader(
            self,
            "Blender Launcher",
            (self.CheckUpdatesButton, self.SettingsButton, self.DocsButton),
        )
        self.header.close_signal.connect(self.close)
        self.header.minimize_signal.connect(self.showMinimized)
        self.CentralLayout.addWidget(self.header)

        # Main content area
        self.main_content_layout = QHBoxLayout()
        self.CentralLayout.addLayout(self.main_content_layout)

        # Sidebar navigation
        self.sidebar = SidebarWidget(self)
        self.main_content_layout.addWidget(self.sidebar)

        self.TabWidget = QTabWidget()
        self.TabWidget.tabBar().hide() # Hide the original tab bar
        self.TabWidget.setProperty("North", True) # Still set property for styling existing TabWidget
        # self.TabWidget.setCornerWidget(self.corner_settings_widget) # Corner widget not needed with sidebar
        self.main_content_layout.addWidget(self.TabWidget)

        # Connect sidebar to main TabWidget
        self.sidebar.index_changed.connect(self.TabWidget.setCurrentIndex)
        self.TabWidget.currentChanged.connect(self.sidebar.set_current_index)


        self.update_system_titlebar(get_use_system_titlebar())
        self.LibraryTab = QWidget()
        self.LibraryTabLayout = QVBoxLayout()
        self.LibraryTabLayout.setContentsMargins(0, 0, 0, 0)
        self.LibraryTab.setLayout(self.LibraryTabLayout)
        self.TabWidget.addTab(self.LibraryTab, "Library")
        self.sidebar.add_tab(self.icons.folder, "Library", 0)

        self.DownloadsTab = QWidget()
        self.DownloadsTabLayout = QVBoxLayout()
        self.DownloadsTabLayout.setContentsMargins(0, 0, 0, 0)
        self.DownloadsTab.setLayout(self.DownloadsTabLayout)
        self.TabWidget.addTab(self.DownloadsTab, "Downloads")
        self.sidebar.add_tab(self.icons.download, "Downloads", 1)

        self.UserTab = QWidget()
        self.UserTabLayout = QVBoxLayout()
        self.UserTabLayout.setContentsMargins(0, 0, 0, 0)
        self.UserTab.setLayout(self.UserTabLayout)
        self.TabWidget.addTab(self.UserTab, "Favorites")
        self.sidebar.add_tab(self.icons.favorite, "Favorites", 2)

        # Placeholder for settings tab in QTabWidget, settings dialog will be shown on button click
        self.SettingsPlaceholderTab = QWidget()
        self.TabWidget.addTab(self.SettingsPlaceholderTab, "Settings")
        self.sidebar.add_tab(self.icons.settings, "Settings", 3)

        # Connect the settings sidebar button to show the settings window
        self.sidebar.button_group.button(3).clicked.connect(self.show_settings_window)

        self.sidebar.add_spacer()

        self.LibraryToolBox = BaseToolBoxWidget(self)
        self.DownloadsToolBox = BaseToolBoxWidget(self)
        self.UserToolBox = BaseToolBoxWidget(self)

        self.toggle_sync_library_and_downloads_pages(get_sync_library_and_downloads_pages())

        self.LibraryTabLayout.addWidget(self.LibraryToolBox)
        self.DownloadsTabLayout.addWidget(self.DownloadsToolBox)
        self.UserTabLayout.addWidget(self.UserToolBox)

        self.LibraryStablePageWidget = BasePageWidget(
            parent=self,
            page_name="LibraryStableListWidget",
            time_label="Commit Time",
            info_text="Nothing to show yet",
            extended_selection=True,
        )
        self.LibraryStableListWidget = self.LibraryToolBox.add_page_widget(self.LibraryStablePageWidget, "Stable")

        self.LibraryDailyPageWidget = BasePageWidget(
            parent=self,
            page_name="LibraryDailyListWidget",
            time_label="Commit Time",
            info_text="Nothing to show yet",
            extended_selection=True,
        )
        self.LibraryDailyListWidget = self.LibraryToolBox.add_page_widget(self.LibraryDailyPageWidget, "Daily")

        self.LibraryExperimentalPageWidget = BasePageWidget(
            parent=self,
            page_name="LibraryExperimentalListWidget",
            time_label="Commit Time",
            info_text="Nothing to show yet",
            extended_selection=True,
        )
        self.LibraryExperimentalListWidget = self.LibraryToolBox.add_page_widget(
            self.LibraryExperimentalPageWidget, "Experimental"
        )

        self.LibraryBFAPageWidget = BasePageWidget(
            parent=self,
            page_name="LibraryBFAListWidget",
            time_label="Commit Time",
            info_text="Nothing to show yet",
            extended_selection=True,
        )
        self.LibraryBFAListWidget = self.LibraryToolBox.add_page_widget(self.LibraryBFAPageWidget, "Bforartists")

        self.DownloadsStablePageWidget = BasePageWidget(
            parent=self,
            page_name="DownloadsStableListWidget",
            time_label="Upload Time",
            info_text="No new builds available",
        )
        self.DownloadsStableListWidget = self.DownloadsToolBox.add_page_widget(self.DownloadsStablePageWidget, "Stable")

        self.DownloadsDailyPageWidget = BasePageWidget(
            parent=self,
            page_name="DownloadsDailyListWidget",
            time_label="Upload Time",
            info_text="No new builds available",
        )
        self.DownloadsDailyListWidget = self.DownloadsToolBox.add_page_widget(self.DownloadsDailyPageWidget, "Daily")

        self.DownloadsExperimentalPageWidget = BasePageWidget(
            parent=self,
            page_name="DownloadsExperimentalListWidget",
            time_label="Upload Time",
            info_text="No new builds available",
        )
        self.DownloadsExperimentalListWidget = self.DownloadsToolBox.add_page_widget(
            self.DownloadsExperimentalPageWidget, "Experimental"
        )

        self.DownloadsBFAPageWidget = BasePageWidget(
            parent=self,
            page_name="DownloadsBFAListWidget",
            time_label="Upload Time",
            info_text="No new builds available",
        )
        self.DownloadsBFAListWidget = self.DownloadsToolBox.add_page_widget(self.DownloadsBFAPageWidget, "Bforartists")

        self.UserFavoritesListWidget = BasePageWidget(
            parent=self, page_name="UserFavoritesListWidget", time_label="Commit Time", info_text="Nothing to show yet"
        )
        self.UserFavoritesListWidget = self.UserToolBox.add_page_widget(self.UserFavoritesListWidget, "Favorites")

        self.UserCustomPageWidget = BasePageWidget(
            parent=self,
            page_name="UserCustomListWidget",
            time_label="Commit Time",
            info_text="Nothing to show yet",
            show_reload=True,
            extended_selection=True,
        )
        self.UserCustomListWidget = self.LibraryToolBox.add_page_widget(self.UserCustomPageWidget, "Custom")

        # Collect all page widgets for column width synchronization
        self._all_page_widgets = [
            self.LibraryStablePageWidget,
            self.LibraryDailyPageWidget,
            self.LibraryExperimentalPageWidget,
            self.LibraryBFAPageWidget,
            self.DownloadsStablePageWidget,
            self.DownloadsDailyPageWidget,
            self.DownloadsExperimentalPageWidget,
            self.DownloadsBFAPageWidget,
            self.UserCustomPageWidget,
        ]
        self._syncing_column_widths = False  # Guard against recursion
        # Connect all page widgets to sync column widths
        for page_widget in self._all_page_widgets:
            page_widget.column_widths_changed.connect(self._sync_column_widths)

        self.TabWidget.setCurrentIndex(get_default_tab())
        self.LibraryToolBox.setCurrentIndex(get_default_library_page())
        self.DownloadsToolBox.setCurrentIndex(get_default_downloads_page())

        self.update_visible_lists()

        # Status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.setContentsMargins(0, 0, 0, 2)
        self.status_bar.setFont(self.font_10)
        self.statusbarLabel = QLabel()
        
        self.NewVersionButton = QPushButton()
        self.NewVersionButton.hide()
        self.NewVersionButton.clicked.connect(self.show_update_window)
        self.statusbarVersion = QPushButton(str(self.version))
        self.statusbarVersion.clicked.connect(self.show_changelog)
        self.statusbarVersion.setToolTip(
            "The version of Blender Launcher that is currently run. Press to check changelog."
        )
        # self.status_bar.addPermanentWidget(self.ForceCheckNewBuilds)
        # self.status_bar.addPermanentWidget(QLabel("│"))
        # self.status_bar.addPermanentWidget(self.statusbarLabel)
        self.status_bar.addPermanentWidget(QLabel(""), 1)
        self.status_bar.addPermanentWidget(self.NewVersionButton)
        self.status_bar.addPermanentWidget(self.statusbarVersion)

        # Draw library
        self.draw_library()

        # Setup tray icon context Menu
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_)
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.close)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show)
        show_favorites_action = QAction(self.icons.favorite, "Favorites", self)
        show_favorites_action.triggered.connect(self.show_favorites)
        quick_launch_action = QAction(self.icons.quick_launch, "Blender", self)
        quick_launch_action.triggered.connect(self.quick_launch)

        self.tray_menu = BaseMenuWidget(parent=self)
        self.tray_menu.setFont(self.font_10)
        self.tray_menu.addActions(
            [
                quick_launch_action,
                show_favorites_action,
                show_action,
                hide_action,
                quit_action,
            ]
        )

        # Setup tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.icons.taskbar)
        self.tray_icon.setToolTip("Blender Launcher")
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.messageClicked.connect(self._show)

        # Linux doesn't handle QSystemTrayIcon.Context activation reason,
        # so add context menu as regular one
        if self.platform == "Linux":
            self.tray_icon.setContextMenu(self.tray_menu)

        # Force style update
        if polish is True:
            style = self.style()
            assert style is not None
            style.unpolish(self.app)
            style.polish(self.app)

        # Show window
        if is_frozen():
            if get_show_tray_icon():
                self.tray_icon.show()

                if get_launch_minimized_to_tray() is False:
                    self._show()
            else:
                self.tray_icon.hide()
                self._show()
        else:
            self.tray_icon.show()
            self._show()

        if get_enable_quick_launch_key_seq() is True:
            self.setup_global_hotkeys_listener()

    def setup_global_hotkeys_listener(self):
        if self.hk_listener is not None:
            self.hk_listener.stop()
        if HOTKEYS_AVAILABLE:
            key_seq = get_quick_launch_key_seq()
            keys = key_seq.split("+")

            for key in keys:
                if len(key) > 1:
                    key_seq = key_seq.replace(key, "<" + key + ">")

            try:
                self.hk_listener = keyboard.GlobalHotKeys({key_seq: self.on_activate_quick_launch})
            except Exception:
                self.dlg = PopupWindow(
                    parent=self,
                    title="Warning",
                    message="Global hotkey sequence was not recognized!<br>Try to use another combination of keys",
                    icon=PopupIcon.WARNING,
                    info_popup=True,
                )
                return

            self.hk_listener.start()

    def on_activate_quick_launch(self):
        if self.settings_window is None:
            self.quick_launch()

    def show_changelog(self):
        url = f"https://github.com/Victor-IX/Blender-Launcher-V2/releases/tag/v{self.version!s}"
        webbrowser.open(url)

    def open_docs(self):
        webbrowser.open("https://Victor-IX.github.io/Blender-Launcher-V2")

    def is_downloading_idle(self):
        download_widgets = []

        download_widgets.extend(self.DownloadsStableListWidget.items())
        download_widgets.extend(self.DownloadsDailyListWidget.items())
        download_widgets.extend(self.DownloadsExperimentalListWidget.items())

        return all(widget.state == DownloadState.IDLE for widget in download_widgets)

    def show_update_window(self):
        if not self.is_downloading_idle():
            self.dlg = PopupWindow(
                parent=self,
                title="Warning",
                message="In order to update Blender Launcher<br> \
                        complete all active downloads!",
                icon=PopupIcon.WARNING,
                info_popup=True,
            )

            return

        # Create copy of 'Blender Launcher.exe' file
        # to act as an updater program
        bl_exe, blu_exe = get_launcher_name()

        cwd = get_cwd()
        source = cwd / bl_exe
        dist = cwd / blu_exe
        shutil.copy(source, dist)

        # Run 'Blender Launcher Updater.exe' with '-update' flag
        if self.platform == "Windows":
            _popen([dist.as_posix(), "--instanced", "update", self.latest_tag])
        elif self.platform == "Linux":
            os.chmod(dist.as_posix(), 0o744)
            _popen(f'nohup "{dist.as_posix()}" --instanced update {self.latest_tag}')

        # Destroy currently running Blender Launcher instance
        self.instance_handler.server.close()
        self.destroy()

    def _show(self):
        if self.isMinimized():
            self.showNormal()

        self.show()
        self.activateWindow()

        self.set_status()
        self.show_signal.emit()

        # TODO: Reimplement custom button on the window taskbar app preview previewer (Launch and Quit)
        # Add custom toolbar icons
        # if self.platform == "Windows":
        #     self.thumbnail_toolbar = QWinThumbnailToolBar(self)
        #     self.thumbnail_toolbar.setWindow(self.windowHandle())

        #     self.toolbar_quick_launch_btn = QWinThumbnailToolButton(self.thumbnail_toolbar)
        #     self.toolbar_quick_launch_btn.setIcon(self.icons.quick_launch)
        #     self.toolbar_quick_launch_btn.setToolTip("Quick Launch")
        #     self.toolbar_quick_launch_btn.clicked.connect(self.quick_launch)
        #     self.thumbnail_toolbar.addButton(self.toolbar_quick_launch_btn)

        #     self.toolbar_quit_btn = QWinThumbnailToolButton(self.thumbnail_toolbar)
        #     self.toolbar_quit_btn.setIcon(self.icons.close)
        #     self.toolbar_quit_btn.setToolTip("Quit")
        #     self.toolbar_quit_btn.clicked.connect(self.quit_)
        #     self.thumbnail_toolbar.addButton(self.toolbar_quit_btn)

    def show_message(self, message, value=None, message_type=None):
        if (
            (message_type == MessageType.DOWNLOADFINISHED and not get_enable_download_notifications())
            or (message_type == MessageType.NEWBUILDS and not get_enable_new_builds_notifications())
            or (message_type == MessageType.ERROR and not get_make_error_popup())
        ):
            return

        if value not in self.notification_pool:
            if value is not None:
                self.notification_pool.append(value)
            self.tray_icon.showMessage("Blender Launcher", message, self.icons.taskbar, 10000)

    def message_from_error(self, err: Exception):
        self.show_message(f"An error has occurred: {err}\nSee the logs for more details.", MessageType.ERROR)
        logger.error(err)

    def message_from_worker(self, w, message, message_type=None):
        logger.debug(f"{w} ({message_type}): {message}")
        self.show_message(f"{w}: {message}", message_type)

    @Slot(TaskWorker)
    def on_worker_creation(self, w: TaskWorker):
        w.error.connect(self.message_from_error)
        w.message.connect(partial(self.message_from_worker, w))

    def show_favorites(self):
        self.TabWidget.setCurrentWidget(self.UserTab)
        self.UserToolBox.setCurrentWidget(self.UserFavoritesListWidget)
        self._show()

    def quick_launch(self):
        try:
            assert self.favorite
            self.favorite.launch()
        except Exception:
            self.quick_launch_fail_signal.emit()

    def quick_launch_fail(self):
        self.dlg = PopupWindow(
            parent=self,
            message="Add build to Quick Launch via<br>\
                        context menu to run it from tray",
            info_popup=True,
        )

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.quick_launch()
            # INFO: Middle click dose not work anymore on new Windows versions with PyQt5
            # Middle click currently return the Trigger reason
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.tray_menu.trigger()

    def stop_auto_scrape_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def schedule_auto_scrape_timer(self):
        self.stop_auto_scrape_timer()

        if not get_check_for_new_builds_automatically():
            return

        interval_seconds = get_new_builds_check_frequency() * 3600

        if interval_seconds <= 0:
            return

        def trigger_auto_scrape():
            self.timer = None
            QTimer.singleShot(0, self.draw_downloads)

        self.timer = threading.Timer(interval_seconds, trigger_auto_scrape)
        self.timer.daemon = True
        self.timer.start()

    def destroy(self):
        self.quit_signal.emit()
        self.stop_auto_scrape_timer()
        self.tray_icon.hide()
        self.app.quit()

    def draw_library(self, clear=False):
        self.set_status("Reading local builds", False)

        if clear:
            self.cm = ConnectionManager(version=self.version, proxy_type=get_proxy_type())
            self.cm.setup()
            self.cm.error.connect(self.connection_error)
            self.manager = self.cm.manager

            self.stop_auto_scrape_timer()
            if self.scraper is not None:
                self.scraper.quit()
            self.DownloadsStableListWidget.clear_()
            self.DownloadsDailyListWidget.clear_()
            self.DownloadsExperimentalListWidget.clear_()
            self.DownloadsBFAListWidget.clear_()
            self.started = True

        self.favorite = None

        self.LibraryStableListWidget.clear_()
        self.LibraryDailyListWidget.clear_()
        self.LibraryExperimentalListWidget.clear_()
        self.LibraryBFAListWidget.clear_()
        self.UserCustomListWidget.clear_()

        self.library_drawer = DrawLibraryTask()
        self.library_drawer.found.connect(self.draw_to_library)
        self.library_drawer.unrecognized.connect(self.draw_unrecognized)
        if not self.offline:
            self.library_drawer.finished.connect(self.draw_downloads)

        self.task_queue.append(self.library_drawer)

    def reload_custom_builds(self):
        self.UserCustomListWidget.clear_()

        self.library_drawer = DrawLibraryTask(["custom"])
        self.library_drawer.found.connect(self.draw_to_library)
        self.library_drawer.unrecognized.connect(self.draw_unrecognized)
        self.task_queue.append(self.library_drawer)

    def draw_downloads(self):
        if get_check_for_new_builds_on_startup():
            self.start_scraper()
        else:
            self.ready_to_scrape()

        self.scraper_finished_signal.connect(self.check_library_for_updates)

    def check_library_for_updates(self):
        all_downloads = []
        all_downloads.extend(self.DownloadsStableListWidget.findChildren(DownloadWidget))
        all_downloads.extend(self.DownloadsDailyListWidget.findChildren(DownloadWidget))
        all_downloads.extend(self.DownloadsExperimentalListWidget.findChildren(DownloadWidget))
        all_downloads.extend(self.DownloadsBFAListWidget.findChildren(DownloadWidget))

        for library_list in [
            self.LibraryStableListWidget,
            self.LibraryDailyListWidget,
            self.LibraryExperimentalListWidget,
            self.LibraryBFAListWidget,
        ]:
            for item in range(library_list.count()):
                widget_item = library_list.item(item)
                if widget_item:
                    library_widget = library_list.itemWidget(widget_item)
                    if library_widget and hasattr(library_widget, "check_for_updates"):
                        library_widget.check_for_updates(all_downloads)

    def connection_error(self):
        logger.error("Connection_error")

        utcnow = strftime(("%H:%M"), localtime())
        self.set_status("Error: connection failed at " + utcnow)
        self.app_state = AppState.IDLE

        if get_check_for_new_builds_automatically() is True:
            self.schedule_auto_scrape_timer()

    @Slot(str)
    def scraper_error(self, s: str):
        self.DownloadsStablePageWidget.set_info_label_text(s)

    def force_check(self):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:  # Shift held while pressing check
            # Ignore scrape_stable, scrape_automated and scrape_bfa settings and scrape all that are visible
            show_stable = get_show_stable_builds()
            show_daily = get_show_daily_builds()
            show_expatch = get_show_experimental_and_patch_builds()
            show_bfa = get_show_bfa_builds()
            self.start_scraper(show_stable, show_daily or show_expatch, show_bfa)
            self.update_visible_lists(
                force_s_stable=show_stable,
                force_s_daily=show_daily,
                force_s_expatch=show_expatch,
                force_s_bfa=show_bfa,
            )
        else:
            # Use settings
            self.start_scraper()
            self.update_visible_lists()

    def start_scraper(self, scrape_stable=None, scrape_daily=None, scrape_expatch=None, scrape_bfa=None):
        self.set_status("Checking for new builds", False)
        self.stop_auto_scrape_timer()

        if scrape_stable is None:
            scrape_stable = get_scrape_stable_builds()
        if scrape_daily is None:
            scrape_daily = get_scrape_daily_builds()
        if scrape_expatch is None:
            scrape_expatch = get_scrape_experimental_builds()
        if scrape_bfa is None:
            scrape_bfa = get_scrape_bfa_builds()

        if scrape_stable:
            self.DownloadsStablePageWidget.set_info_label_text("Checking for new builds")
        else:
            self.DownloadsStablePageWidget.set_info_label_text("Checking for stable builds is disabled")

        if scrape_daily:
            self.DownloadsDailyPageWidget.set_info_label_text("Checking for new builds")
        else:
            self.DownloadsDailyPageWidget.set_info_label_text("Checking for daily builds is disabled")

        if scrape_expatch:
            self.DownloadsExperimentalPageWidget.set_info_label_text("Checking for new builds")
        else:
            self.DownloadsExperimentalPageWidget.set_info_label_text("Checking for experimental builds is disabled")

        if scrape_bfa:
            self.DownloadsBFAPageWidget.set_info_label_text("Checking for new builds")
        else:
            self.DownloadsBFAPageWidget.set_info_label_text("Checking for Bforartists builds is disabled")

        # Sometimes these builds end up being invalid, particularly when new builds are available, which, there usually
        # are at least once every two days. They are so easily gathered there's little loss here
        self.DownloadsDailyListWidget.clear_()
        self.DownloadsExperimentalListWidget.clear_()
        self.DownloadsBFAListWidget.clear_()

        self.cashed_builds.clear()
        self.new_downloads = False
        self.app_state = AppState.CHECKINGBUILDS

        self.scraper.scrape_stable = scrape_stable
        self.scraper.scrape_daily = scrape_daily
        self.scraper.scrape_experimental = scrape_expatch
        self.scraper.scrape_bfa = scrape_bfa
        self.scraper.manager = self.cm
        self.scraper.start()

    def scraper_finished(self):
        if self.new_downloads:
            self.show_message("New builds of Blender are available!", message_type=MessageType.NEWBUILDS)

        for list_widget in self.DownloadsToolBox.list_widgets:
            for widget in list_widget.widgets.copy():
                if widget.build_info not in self.cashed_builds:
                    widget.destroy()

        utcnow = localtime()
        dt = datetime.fromtimestamp(mktime(utcnow)).astimezone()
        set_last_time_checked_utc(dt)
        self.last_time_checked = dt
        self.app_state = AppState.IDLE

        if get_check_for_new_builds_automatically() is True:
            self.schedule_auto_scrape_timer()
            self.started = False
        else:
            self.stop_auto_scrape_timer()
        self.ready_to_scrape()

    def ready_to_scrape(self):
        self.app_state = AppState.IDLE
        self.set_status("Last check at " + self.last_time_checked.strftime(DATETIME_FORMAT), True)
        self.scraper_finished_signal.emit()

    def draw_from_cashed(self, build_info):
        if self.app_state == AppState.IDLE:
            for cashed_build in self.cashed_builds:
                if build_info == cashed_build:
                    self.draw_to_downloads(cashed_build)
                    return

    def draw_to_downloads(self, build_info: BuildInfo):
        if self.started and build_info.commit_time < self.last_time_checked:
            is_new = False
        else:
            is_new = True

        if build_info not in self.cashed_builds:
            self.cashed_builds.append(build_info)

        branch = build_info.branch

        if branch in ("stable", "lts"):
            downloads_list_widget = self.DownloadsStableListWidget
            library_list_widget = self.LibraryStableListWidget
        elif branch == "daily":
            downloads_list_widget = self.DownloadsDailyListWidget
            library_list_widget = self.LibraryDailyListWidget
        elif branch == "bforartists":
            downloads_list_widget = self.DownloadsBFAListWidget
            library_list_widget = self.LibraryBFAListWidget
        else:
            downloads_list_widget = self.DownloadsExperimentalListWidget
            library_list_widget = self.LibraryExperimentalListWidget

        if not downloads_list_widget.contains_build_info(build_info):
            installed = library_list_widget.widget_with_blinfo(build_info)
            item = BaseListWidgetItem(build_info.commit_time)
            widget = DownloadWidget(
                self,
                downloads_list_widget,
                item,
                build_info,
                installed=installed,
                show_new=is_new,
            )
            widget.focus_installed_widget.connect(self.focus_widget)
            downloads_list_widget.add_item(item, widget)
            if is_new:
                self.new_downloads = True

    def draw_to_library(self, path: Path, show_new=False):
        branch = Path(path).parent.name

        if branch in ("stable", "lts"):
            library = self.LibraryStableListWidget
            download = self.DownloadsStableListWidget
        elif branch == "daily":
            library = self.LibraryDailyListWidget
            download = self.DownloadsDailyListWidget
        elif branch == "experimental":
            library = self.LibraryExperimentalListWidget
            download = self.DownloadsExperimentalListWidget
        elif branch == "bforartists":
            library = self.LibraryBFAListWidget
            download = self.DownloadsBFAListWidget
        elif branch == "custom":
            library = self.UserCustomListWidget
            download = None
        else:
            return None

        item = BaseListWidgetItem()
        widget = LibraryWidget(self, item, path, library, show_new)

        if download is not None:

            def _initialized():
                dlw: DownloadWidget | None = download.widget_with_blinfo(widget.build_info)
                if dlw is not None and not dlw.installed:
                    dlw.setInstalled(widget)

            widget.initialized.connect(_initialized)

        library.insert_item(item, widget)
        return widget

    def draw_unrecognized(self, path):
        branch = Path(path).parent.name

        if branch in ("stable", "lts"):
            list_widget = self.LibraryStableListWidget
        elif branch in ("daily", "experimental"):
            list_widget = self.LibraryDailyListWidget
        elif branch == "bforartists":
            list_widget = self.LibraryBFAListWidget
        elif branch == "custom":
            list_widget = self.UserCustomListWidget
        else:
            return

        item = BaseListWidgetItem()
        widget = UnrecoBuildWidget(self, path, list_widget, item)

        list_widget.insert_item(item, widget)

    def update_visible_lists(
        self,
        force_l_stable=False,  # Force the library visibility of these
        force_l_daily=False,
        force_l_expatch=False,
        force_l_bfa=False,
        force_s_stable=False,  # Force the scraper visibility of these
        force_s_daily=False,
        force_s_expatch=False,
        force_s_bfa=False,
    ):
        show_stable = force_l_stable or get_show_stable_builds()
        show_daily = force_l_daily or get_show_daily_builds()
        show_expatch = force_l_expatch or get_show_experimental_and_patch_builds()
        show_bfa = force_l_bfa or get_show_bfa_builds()
        scrape_stable = force_s_stable or get_scrape_stable_builds()
        scrape_daily = force_s_daily or get_scrape_daily_builds()
        scrape_expatch = force_s_expatch or get_scrape_experimental_builds()
        scrape_bfa = force_s_bfa or get_scrape_bfa_builds()

        self.LibraryToolBox.setTabVisible(0, show_stable)
        self.LibraryToolBox.setTabEnabled(0, show_stable)
        self.LibraryToolBox.setTabVisible(1, show_daily)
        self.LibraryToolBox.setTabEnabled(1, show_daily)
        self.LibraryToolBox.setTabVisible(2, show_expatch)
        self.LibraryToolBox.setTabEnabled(2, show_expatch)
        self.LibraryToolBox.setTabVisible(3, show_bfa)
        self.LibraryToolBox.setTabEnabled(3, show_bfa)
        self.DownloadsToolBox.setTabVisible(0, scrape_stable)
        self.DownloadsToolBox.setTabEnabled(0, scrape_stable)
        self.DownloadsToolBox.setTabVisible(1, scrape_daily)
        self.DownloadsToolBox.setTabEnabled(1, scrape_daily)
        self.DownloadsToolBox.setTabVisible(2, scrape_expatch)
        self.DownloadsToolBox.setTabEnabled(2, scrape_expatch)
        self.DownloadsToolBox.setTabVisible(3, scrape_bfa)
        self.DownloadsToolBox.setTabEnabled(3, scrape_bfa)

    def focus_widget(self, widget: LibraryWidget):
        tab = self.LibraryTab
        item = widget.item
        lst = item.listWidget()

        assert lst is not None
        self.TabWidget.setCurrentWidget(tab)
        lst.setFocus(Qt.FocusReason.ShortcutFocusReason)
        widget.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def set_status(self, status=None, is_force_check_on=None):
        if status is not None:
            self.status = status

        if is_force_check_on is not None:
            self.is_force_check_on = is_force_check_on

        self.ForceCheckNewBuilds.setEnabled(self.is_force_check_on)
        self.statusbarLabel.setText(self.status)

    def set_version(self, latest_tag, path_note):
        if self.version.build is not None and "dev" in self.version.build:
            return
        latest = Version.parse(latest_tag[1:])

        # Set the verison to 0.0.0 to force update to the latest stable version
        if not get_use_pre_release_builds() and self.version.prerelease is not None and "rc" in self.version.prerelease:
            current = Version(0, 0, 0)
        else:
            current = self.version

        logging.debug(f"Latest version on GitHub is {latest}")

        if latest > current:
            self.NewVersionButton.setText(f"Update to version {latest_tag.replace('v', '')}")
            self.NewVersionButton.show()
            self.latest_tag = latest_tag
            if path_note is not None:
                path_note_text = patch_note_cleaner(path_note)
            popup = PopupWindow(
                title=f"New version {latest_tag.replace('v', '')} available",
                message=path_note_text,
                buttons=["Update", "Later"],
                icon=PopupIcon.NONE,
                parent=self,
            )
            popup.accepted.connect(self.show_update_window)

        else:
            self.NewVersionButton.hide()

    def show_settings_window(self):
        self.settings_window = SettingsWindow(parent=self)

    def clear_temp(self, path=None):
        if path is None:
            path = Path(get_library_folder()) / ".temp"
        a = RemovalTask(path)
        self.task_queue.append(a)

    def quit_(self):
        busy = self.task_queue.get_busy_threads()
        if any(busy):
            self.dlg = PopupWindow(
                parent=self,
                title="Warning",
                message=(
                    "Some tasks are still in progress!<br>"
                    + "\n".join([f" - {item}<br>" for worker, item in busy.items()])
                    + "Are you sure you want to quit?"
                ),
                buttons=["Yes", "No"],
                icon=PopupIcon.WARNING,
            )

            self.dlg.accepted.connect(self.destroy)
            return

        self.destroy()

    @Slot(int, int, int)
    def _sync_column_widths(self, version_width: int, branch_width: int, commit_time_width: int):
        """Synchronize column widths across all page widgets."""
        if self._syncing_column_widths:
            return
        self._syncing_column_widths = True
        sizes = [version_width, branch_width, commit_time_width]
        for page_widget in self._all_page_widgets:
            # Block signals to prevent infinite loop from splitter
            page_widget.headerSplitter.blockSignals(True)
            page_widget.headerSplitter.setSizes(sizes)
            page_widget.headerSplitter.blockSignals(False)
            # Emit signal to update list items in this page
            page_widget.column_widths_changed.emit(version_width, branch_width, commit_time_width)
        self._syncing_column_widths = False

    def closeEvent(self, event):
        if get_show_tray_icon():
            if not get_tray_icon_notified():
                self.show_message(
                    "Blender Launcher is minimized to the system tray. "
                    '\nDisable "Show Tray Icon" in the settings to disable this.'
                )
                set_tray_icon_notified()
            event.ignore()
            self.hide()
            self.close_signal.emit()
        else:
            self.quit_()

    def restart_app(self, cwd: Path | None = None):
        """Launch 'Blender Launcher.exe' and exit"""
        cwd = cwd or get_cwd()

        if self.platform == "Windows":
            exe = (cwd / "Blender Launcher.exe").as_posix()
            _popen([exe, "-instanced"])
        elif self.platform == "Linux":
            exe = (cwd / "Blender Launcher").as_posix()
            os.chmod(exe, 0o744)
            _popen('nohup "' + exe + '" -instanced')
        elif self.platform == "macOS":
            # sys.executable should be something like /.../Blender Launcher.app/Contents/MacOS/Blender Launcher
            app = Path(sys.executable).parent.parent.parent
            _popen(f"open -n {shlex.quote(str(app))}")

        self.destroy()
