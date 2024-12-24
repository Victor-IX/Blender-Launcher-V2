from __future__ import annotations

import logging
import os
import re
import shlex
import shutil
import sys
import webbrowser
from datetime import datetime, timezone
from enum import Enum
from functools import partial
from pathlib import Path
from platform import version
from time import localtime, mktime, strftime
from typing import TYPE_CHECKING

from items.base_list_widget_item import BaseListWidgetItem
from modules._platform import _popen, get_cwd, get_launcher_name, get_platform, is_frozen
from modules._resources_rc import RESOURCES_AVAILABLE
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
    get_last_time_checked_utc,
    get_launch_minimized_to_tray,
    get_library_folder,
    get_make_error_popup,
    get_proxy_type,
    get_quick_launch_key_seq,
    get_scrape_automated_builds,
    get_scrape_bfa_builds,
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
    is_library_folder_valid,
    set_dont_show_resource_warning,
    set_last_time_checked_utc,
    set_library_folder,
    set_tray_icon_notified,
)
from modules.tasks import Task, TaskQueue, TaskWorker
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtNetwork import QLocalServer
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
from windows.base_window import BaseWindow
from windows.dialog_window import DialogIcon, DialogWindow
from windows.file_dialog_window import FileDialogWindow
from windows.settings_window import SettingsWindow

try:
    from pynput import keyboard

    HOTKEYS_AVAILABLE = True
except Exception as e:
    logging.error(f"Error importing pynput: {e}\nGlobal hotkeys not supported.")
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

    def __init__(self, app: QApplication, version: Version, offline: bool = False, build_cache: bool = False):
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
        self.server = QLocalServer()
        self.server.listen("blender-launcher-server")
        self.quick_launch_fail_signal.connect(self.quick_launch_fail)
        self.server.newConnection.connect(self.new_connection)

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
        self.favorite: BaseBuildWidget | None = None
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
            self.app.aboutToQuit.connect(self._aboutToQuit)

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
            dlg = DialogWindow(
                parent=self,
                title="Error",
                text="Resources failed to load! The launcher will still work,<br> \
                but the style will be broken.",
                accept_text="OK",
                cancel_text="Don't Show Again",
            )
            dlg.cancelled.connect(self.__dont_show_resources_warning_again)

        # Check library folder
        if is_library_folder_valid() is False:
            self.dlg = DialogWindow(
                parent=self,
                title="Setup",
                text="First, choose where Blender<br>builds will be stored",
                accept_text="Continue",
                cancel_text=None,
                icon=DialogIcon.INFO,
            )
            self.dlg.accepted.connect(self.prompt_library_folder)
        else:
            create_library_folders(get_library_folder())
            self.draw()

    def __dont_show_resources_warning_again(self):
        set_dont_show_resource_warning(True)

    def prompt_library_folder(self):
        library_folder = get_cwd().as_posix()
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
                self.dlg = DialogWindow(
                    parent=self,
                    title="Setup",
                    text="The selected path is relative to the executable's path.<br>\
                        Would you like to save it as relative?<br>\
                        This is useful if the folder may move.",
                    accept_text="Yes",
                    cancel_text="No",
                )
                self.dlg.accepted.connect(lambda: self.set_library_folder(folder, True))
                self.dlg.cancelled.connect(lambda: self.set_library_folder(folder, False))
                return

            if relative:
                folder = folder.relative_to(get_cwd())

        if set_library_folder(str(folder)) is True:
            self.draw(True)
        else:
            self.dlg = DialogWindow(
                parent=self,
                title="Warning",
                text="Selected folder is not valid or<br>\
                doesn't have write permissions!",
                accept_text="Retry",
                cancel_text=None,
            )
            self.dlg.accepted.connect(self.prompt_library_folder)

    def update_system_titlebar(self, b: bool):
        for window in self.windows:
            window.set_system_titlebar(b)
            if window is not self:
                window.update_system_titlebar(b)
        self.header.setHidden(b)
        self.corner_settings_widget.setHidden(not b)

    def draw(self, polish=False):
        # Header
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
            (self.SettingsButton, self.DocsButton),
        )
        self.header.close_signal.connect(self.attempt_close)
        self.header.minimize_signal.connect(self.showMinimized)
        self.CentralLayout.addWidget(self.header)

        # Tab layout
        self.TabWidget = QTabWidget()
        self.TabWidget.setProperty("North", True)
        self.TabWidget.setCornerWidget(self.corner_settings_widget)
        self.CentralLayout.addWidget(self.TabWidget)

        self.update_system_titlebar(get_use_system_titlebar())
        self.LibraryTab = QWidget()
        self.LibraryTabLayout = QVBoxLayout()
        self.LibraryTabLayout.setContentsMargins(0, 0, 0, 0)
        self.LibraryTab.setLayout(self.LibraryTabLayout)
        self.TabWidget.addTab(self.LibraryTab, "Library")

        self.DownloadsTab = QWidget()
        self.DownloadsTabLayout = QVBoxLayout()
        self.DownloadsTabLayout.setContentsMargins(0, 0, 0, 0)
        self.DownloadsTab.setLayout(self.DownloadsTabLayout)
        self.TabWidget.addTab(self.DownloadsTab, "Downloads")

        self.UserTab = QWidget()
        self.UserTabLayout = QVBoxLayout()
        self.UserTabLayout.setContentsMargins(0, 0, 0, 0)
        self.UserTab.setLayout(self.UserTabLayout)
        self.TabWidget.addTab(self.UserTab, "Favorites")

        self.LibraryToolBox = BaseToolBoxWidget(self)
        self.DownloadsToolBox = BaseToolBoxWidget(self)
        self.UserToolBox = BaseToolBoxWidget(self)

        self.toggle_library_and_downloads_pages()

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
        self.ForceCheckNewBuilds = QPushButton("Check")
        self.ForceCheckNewBuilds.setEnabled(False)
        self.ForceCheckNewBuilds.setToolTip(
            "Check for new builds online<br>\
            (Hold SHIFT to force check stable and automated builds)"
        )
        self.ForceCheckNewBuilds.clicked.connect(self.force_check)
        self.NewVersionButton = QPushButton()
        self.NewVersionButton.hide()
        self.NewVersionButton.clicked.connect(self.show_update_window)
        self.statusbarVersion = QPushButton(str(self.version))
        self.statusbarVersion.clicked.connect(self.show_changelog)
        self.statusbarVersion.setToolTip(
            "The version of Blender Launcher that is currently run. Press to check changelog."
        )
        self.status_bar.addPermanentWidget(self.ForceCheckNewBuilds)
        self.status_bar.addPermanentWidget(QLabel("│"))
        self.status_bar.addPermanentWidget(self.statusbarLabel)
        self.status_bar.addPermanentWidget(QLabel(""), 1)
        self.status_bar.addPermanentWidget(self.NewVersionButton)
        self.status_bar.addPermanentWidget(self.statusbarVersion)

        # Draw library
        self.draw_library()

        # Setup tray icon context Menu
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_)
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.attempt_close)
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
                self.dlg = DialogWindow(
                    parent=self,
                    title="Warning",
                    text="Global hotkey sequence was not recognized!<br>Try to use another combination of keys",
                    accept_text="OK",
                    cancel_text=None,
                )
                return

            self.hk_listener.start()

    def on_activate_quick_launch(self):
        if self.settings_window is None:
            self.quick_launch()

    def show_changelog(self):
        url = f"https://github.com/Victor-IX/Blender-Launcher-V2/releases/tag/v{self.version!s}"
        webbrowser.open(url)

    def toggle_library_and_downloads_pages(self):
        if self.isSignalConnected(self.LibraryToolBox, "tab_changed()"):
            self.LibraryToolBox.tab_changed.disconnect()

        if self.isSignalConnected(self.DownloadsToolBox, "tab_changed()"):
            self.DownloadsToolBox.tab_changed.disconnect()

    def isSignalConnected(self, obj, name):
        index = obj.metaObject().indexOfMethod(name)

        if index > -1:
            method = obj.metaObject().method(index)

            if method:
                return obj.isSignalConnected(method)

        return False

    def is_downloading_idle(self):
        download_widgets = []

        download_widgets.extend(self.DownloadsStableListWidget.items())
        download_widgets.extend(self.DownloadsDailyListWidget.items())
        download_widgets.extend(self.DownloadsExperimentalListWidget.items())

        return all(widget.state == DownloadState.IDLE for widget in download_widgets)

    def show_update_window(self):
        if not self.is_downloading_idle():
            self.dlg = DialogWindow(
                parent=self,
                title="Warning",
                text="In order to update Blender Launcher<br> \
                        complete all active downloads!",
                accept_text="OK",
                cancel_text=None,
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
        self.server.close()
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
        self.dlg = DialogWindow(
            parent=self,
            text="Add build to Quick Launch via<br>\
                        context menu to run it from tray",
            accept_text="OK",
            cancel_text=None,
            icon=DialogIcon.INFO,
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

    def kill_thread_with_task(self, task: Task):
        """
        Kills a thread listener using the current action.

        Parameters
        ----------
        action : Action


        Returns
        -------
        bool
            success.
        """
        thread = self.task_queue.thread_with_task(task)
        if thread is not None:
            thread.fullstop()
            return True
        return False

    def destroy(self):
        self.quit_signal.emit()

        if self.timer is not None:
            self.timer.cancel()

        self.tray_icon.hide()
        self.app.quit()

    def draw_library(self, clear=False):
        self.set_status("Reading local builds", False)

        if clear:
            self.cm = ConnectionManager(version=version, proxy_type=get_proxy_type())
            self.cm.setup()
            self.cm.error.connect(self.connection_error)
            self.manager = self.cm.manager

            if self.timer is not None:
                self.timer.cancel()
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

    def connection_error(self):
        print("connection_error")

        utcnow = strftime(("%H:%M"), localtime())
        self.set_status("Error: connection failed at " + utcnow)
        self.app_state = AppState.IDLE

        # if get_check_for_new_builds_automatically() is True:
        #     self.timer = threading.Timer(
        #         get_new_builds_check_frequency(), self.draw_downloads)
        #     self.timer.start()

    @Slot(str)
    def scraper_error(self, s: str):
        self.DownloadsStablePageWidget.set_info_label_text(s)

    def force_check(self):
        if QApplication.keyboardModifiers() & Qt.ShiftModifier:  # Shift held while pressing check
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

    def start_scraper(self, scrape_stable=None, scrape_automated=None, scrape_bfa=None):
        self.set_status("Checking for new builds", False)

        if scrape_stable is None:
            scrape_stable = get_scrape_stable_builds()
        if scrape_automated is None:
            scrape_automated = get_scrape_automated_builds()
        if scrape_bfa is None:
            scrape_bfa = get_scrape_bfa_builds()

        if scrape_stable:
            self.DownloadsStablePageWidget.set_info_label_text("Checking for new builds")
        else:
            self.DownloadsStablePageWidget.set_info_label_text("Checking for stable builds is disabled")

        if scrape_automated:
            msg = "Checking for new builds"
        else:
            msg = "Checking for automated builds is disabled"

        for page in self.DownloadsToolBox.pages:
            if page is not self.DownloadsStablePageWidget:
                page.set_info_label_text(msg)

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
        self.scraper.scrape_automated = scrape_automated
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

        # if get_check_for_new_builds_automatically() is True:
        #     self.timer = threading.Timer(
        #         get_new_builds_check_frequency(), self.draw_downloads)
        #     self.timer.start()
        #     self.started = False
        self.ready_to_scrape()

    def ready_to_scrape(self):
        self.app_state = AppState.IDLE
        self.set_status("Last check at " + self.last_time_checked.strftime(DATETIME_FORMAT), True)

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
        scrape_daily = force_s_daily or (get_scrape_automated_builds() and get_show_daily_builds())
        scrape_expatch = force_s_expatch or (get_scrape_automated_builds() and get_show_experimental_and_patch_builds())
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

    def focus_widget(self, widget: BaseBuildWidget):
        tab: QWidget | None = None
        lst: BaseListWidget | None = None
        item: BaseListWidgetItem | None = None

        if isinstance(widget, LibraryWidget):
            tab = self.LibraryTab
            item = widget.item
            assert item is not None
            lst = item.listWidget()

        assert tab and lst and item
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

    def set_version(self, latest_tag):
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
            self.show_message("New version of Blender Launcher is available!", value=latest_tag)
            self.latest_tag = latest_tag
        else:
            self.NewVersionButton.hide()

    def show_settings_window(self):
        self.settings_window = SettingsWindow(parent=self)

    def clear_temp(self, path=None):
        if path is None:
            path = Path(get_library_folder()) / ".temp"
        a = RemovalTask(path)
        self.task_queue.append(a)

    def _aboutToQuit(self):  # MacOS Target
        self.quit_()

    def quit_(self):
        busy = self.task_queue.get_busy_threads()
        if any(busy):
            self.dlg = DialogWindow(
                parent=self,
                title="Warning",
                text=(
                    "Some tasks are still in progress!<br>"
                    + "\n".join([f" - {item}<br>" for worker, item in busy.items()])
                    + "Are you sure you want to quit?"
                ),
                accept_text="Yes",
                cancel_text="No",
            )

            self.dlg.accepted.connect(self.destroy)
            return

        self.destroy()

    @Slot()
    def attempt_close(self):
        self.close()

    def closeEvent(self, event):
        if get_show_tray_icon():
            if not get_tray_icon_notified():
                self.show_message(
                    "Blender Launcher V2 is minimized to the system tray. "
                    '\nDisable "Show Tray Icon" in the settings to disable this.'
                )
                set_tray_icon_notified()
            event.ignore()
            self.hide()
            self.close_signal.emit()
        else:
            self.quit_()

    def new_connection(self):
        self.socket = self.server.nextPendingConnection()
        assert self.socket is not None
        self.socket.readyRead.connect(self.read_socket_data)
        self._show()

    def read_socket_data(self):
        assert self.socket is not None
        data = self.socket.readAll()

        if str(data, encoding="ascii") != str(self.version):
            self.dlg = DialogWindow(
                parent=self,
                title="Warning",
                text="An attempt to launch a different version<br>\
                      of Blender Launcher was detected!<br>\
                      Please, terminate currently running<br>\
                      version to proceed this action!",
                accept_text="OK",
                cancel_text=None,
                icon=DialogIcon.WARNING,
            )

    def open_docs(self):
        webbrowser.open("https://Victor-IX.github.io/Blender-Launcher-V2")

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasFormat("text/plain"):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        print(e.mimeData().text())

    def restart_app(self):
        """Launch 'Blender Launcher.exe' and exit"""
        cwd = get_cwd()

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
