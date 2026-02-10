from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from i18n import t
from modules.platform_utils import get_platform
from modules.settings import (
    delete_action,
    get_actual_library_folder,
    get_config_file,
    get_default_delete_action,
    get_launch_minimized_to_tray,
    get_launch_timer_duration,
    get_launch_when_system_starts,
    get_library_folder,
    get_purge_temp_on_startup,
    get_show_tray_icon,
    get_use_pre_release_builds,
    get_worker_thread_count,
    migrate_config,
    purge_temp_folder,
    set_auto_register_winget,
    set_default_delete_action,
    set_launch_minimized_to_tray,
    set_launch_timer_duration,
    set_launch_when_system_starts,
    set_library_folder,
    set_purge_temp_on_startup,
    set_show_tray_icon,
    set_use_pre_release_builds,
    set_worker_thread_count,
    user_config,
)
from modules.shortcut import generate_program_shortcut, get_default_program_shortcut_destination
from modules.winget_integration import register_with_winget, unregister_from_winget
from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLabel, QPushButton, QSpinBox
from widgets.folder_select import FolderSelector
from widgets.settings_form_widget import SettingsFormWidget
from widgets.settings_window.settings_group import SettingsGroup
from windows.file_dialog_window import FileDialogWindow
from windows.popup_window import Popup

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class GeneralTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Application Settings

        self.application_settings = SettingsGroup(t("settings.general.app.label"), parent=self)

        # Library Folder
        self.LibraryFolderLabel = QLabel()
        self.LibraryFolderLabel.setText(t("settings.general.app.library_folder"))
        self.LibraryFolder = FolderSelector(parent, default_folder=get_actual_library_folder())
        self.LibraryFolder.validity_changed.connect(self.library_folder_validity_changed)
        self.LibraryFolder.folder_changed.connect(self.set_library_folder_)

        # Launch When System Starts
        self.LaunchWhenSystemStartsCheckBox = QCheckBox()
        self.LaunchWhenSystemStartsCheckBox.setText(t("settings.general.app.system_start"))
        self.LaunchWhenSystemStartsCheckBox.setToolTip(t("settings.general.app.system_start_tooltip"))
        self.LaunchWhenSystemStartsCheckBox.setChecked(get_launch_when_system_starts())
        self.LaunchWhenSystemStartsCheckBox.clicked.connect(set_launch_when_system_starts)

        # Launch Minimized To Tray
        self.LaunchMinimizedToTrayCheckBox = QCheckBox()
        self.LaunchMinimizedToTrayCheckBox.setText(t("settings.general.app.launch_minimized"))
        self.LaunchMinimizedToTrayCheckBox.setToolTip(t("settings.general.app.launch_minimized_tooltip"))
        self.LaunchMinimizedToTrayCheckBox.setChecked(get_launch_minimized_to_tray())
        self.LaunchMinimizedToTrayCheckBox.setEnabled(get_launch_when_system_starts())
        self.LaunchMinimizedToTrayCheckBox.clicked.connect(set_launch_minimized_to_tray)

        # Show Tray Icon
        self.ShowTrayIconCheckBox = QCheckBox()
        self.ShowTrayIconCheckBox.setText(t("settings.general.app.minimize"))
        self.ShowTrayIconCheckBox.setChecked(get_show_tray_icon())
        self.ShowTrayIconCheckBox.clicked.connect(self.toggle_show_tray_icon)
        self.ShowTrayIconCheckBox.setToolTip(t("settings.general.app.minimize_tooltip"))

        # Worker thread count
        self.WorkerThreadCountBox = QLabel()
        self.WorkerThreadCountBox.setText(t("settings.general.app.worker_count"))
        self.WorkerThreadCount = QSpinBox()
        self.WorkerThreadCount.setToolTip(t("settings.general.app.worker_count_tooltip"))
        self.WorkerThreadCount.editingFinished.connect(self.set_worker_thread_count)
        self.WorkerThreadCount.setMinimum(1)
        self.WorkerThreadCount.setValue(get_worker_thread_count())

        # Warn if thread count exceeds cpu count
        cpu_count = os.cpu_count()
        if cpu_count is not None:

            def warn_values_above_cpu(v: int):
                if v > cpu_count:
                    self.WorkerThreadCount.setSuffix(t("settings.general.app.worker_count_warning"))
                else:
                    self.WorkerThreadCount.setSuffix("")

            self.WorkerThreadCount.valueChanged.connect(warn_values_above_cpu)

        # Pre-release builds
        self.PreReleaseBuildsCheckBox = QCheckBox()
        self.PreReleaseBuildsCheckBox.setText(t("settings.general.app.prerelease"))
        self.PreReleaseBuildsCheckBox.setChecked(get_use_pre_release_builds())
        self.PreReleaseBuildsCheckBox.clicked.connect(set_use_pre_release_builds)
        self.PreReleaseBuildsCheckBox.setToolTip(t("settings.general.app.prerelease_tooltip"))

        # Create Shortcut
        self.create_shortcut_button = QPushButton(
            t(
                "general.app.create_shortcut",
                shortcut_type=t(
                    f"general.app.shortcut_type.{get_platform().lower()}",
                ),
            )
        )
        self.create_shortcut_button.clicked.connect(self.create_shortcut)

        # Layout
        self.application_layout = QGridLayout()
        self.application_layout.addWidget(self.LibraryFolderLabel, 0, 0, 1, 1)
        self.application_layout.addWidget(self.LibraryFolder, 1, 0, 1, 3)
        if get_platform() == "Windows":
            self.application_layout.addWidget(self.LaunchWhenSystemStartsCheckBox, 2, 0, 1, 1)
        self.application_layout.addWidget(self.ShowTrayIconCheckBox, 3, 0, 1, 1)
        self.application_layout.addWidget(self.LaunchMinimizedToTrayCheckBox, 4, 0, 1, 1)
        self.application_layout.addWidget(self.WorkerThreadCountBox, 5, 0, 1, 1)
        self.application_layout.addWidget(self.WorkerThreadCount, 5, 1, 1, 2)
        self.application_layout.addWidget(self.PreReleaseBuildsCheckBox, 6, 0, 1, 1)
        self.application_layout.addWidget(self.create_shortcut_button, 7, 0, 1, 3)
        self.application_settings.setLayout(self.application_layout)

        self.addRow(self.application_settings)

        if get_config_file() != user_config():
            self.migrate_button = QPushButton(t("settings.general.migratel2u"), self)
            self.migrate_button.setProperty("CollapseButton", True)
            self.migrate_button.clicked.connect(self.migrate_confirmation)

            self.addRow(self.migrate_button)

        # File Association
        self.file_association_group = SettingsGroup(t("settings.general.file_assoc.label"), parent=self)
        layout = QGridLayout()

        if sys.platform == "win32":
            from modules.shortcut import register_windows_filetypes, unregister_windows_filetypes

            self.register_file_association_button = QPushButton(
                t("settings.general.file_assoc.register"), parent=self.file_association_group
            )
            self.register_file_association_button.setToolTip(t("settings.general.file_assoc.register_tooltip"))

            self.unregister_file_association_button = QPushButton(
                t("settings.general.file_assoc.unregister"), parent=self.file_association_group
            )
            self.unregister_file_association_button.setToolTip(t("settings.general.file_assoc.unregister_tooltip"))
            self.register_file_association_button.clicked.connect(register_windows_filetypes)
            self.register_file_association_button.clicked.connect(self.refresh_association_buttons)
            self.unregister_file_association_button.clicked.connect(unregister_windows_filetypes)
            self.unregister_file_association_button.clicked.connect(self.refresh_association_buttons)
            self.refresh_association_buttons()
            layout.addWidget(self.register_file_association_button, 0, 0, 1, 1)
            layout.addWidget(self.unregister_file_association_button, 0, 1, 1, 1)

        self.launch_timer_duration = QSpinBox()
        self.launch_timer_duration.setToolTip(t("settings.general.file_assoc.launch_timer_duration_tooltip"))
        self.launch_timer_duration.setRange(-1, 120)
        self.launch_timer_duration.setValue(get_launch_timer_duration())
        self.launch_timer_duration.valueChanged.connect(self.set_launch_timer_duration)
        self.set_launch_timer_duration()
        layout.addWidget(QLabel(t("settings.general.file_assoc.launch_timer_duration")), 1, 0, 1, 1)
        layout.addWidget(self.launch_timer_duration, 1, 1, 1, 1)

        self.file_association_group.setLayout(layout)
        self.addRow(self.file_association_group)

        # WinGet Integration
        if get_platform() == "Windows":
            self.winget_group = SettingsGroup(t("settings.general.winget.label"), parent=self)
            winget_layout = QGridLayout()

            winget_info = QLabel(t("settings.general.winget.info"))
            winget_info.setWordWrap(True)

            self.register_winget_button = QPushButton(t("settings.general.winget.register"), parent=self.winget_group)
            self.register_winget_button.setToolTip(t("settings.general.winget.register_tooltip"))

            self.unregister_winget_button = QPushButton(
                t("settings.general.winget.unregister"),
                parent=self.winget_group,
            )
            self.unregister_winget_button.setToolTip(t("settings.general.winget.unregister_tooltip"))

            self.register_winget_button.clicked.connect(self.register_with_winget)
            self.unregister_winget_button.clicked.connect(self.unregister_from_winget)
            self.refresh_winget_buttons()

            winget_layout.addWidget(winget_info, 0, 0, 1, 2)
            winget_layout.addWidget(self.register_winget_button, 1, 0, 1, 1)
            winget_layout.addWidget(self.unregister_winget_button, 1, 1, 1, 1)

            self.winget_group.setLayout(winget_layout)
            self.addRow(self.winget_group)

        self.advanced_settings = SettingsGroup(t("settings.general.advanced.label"), parent=self)
        self.default_delete_action = QComboBox()
        self.default_delete_action.addItems(delete_action.keys())
        self.default_delete_action.setToolTip(t("settings.general.advanced.default_delete_action_tooltip"))
        self.default_delete_action.setCurrentIndex(get_default_delete_action())
        self.default_delete_action.activated[int].connect(self.change_default_delete_action)

        # Purge Temp on Startup
        self.PurgeTempOnStartupCheckBox = QCheckBox()
        self.PurgeTempOnStartupCheckBox.setText(t("settings.general.advanced.purge_temp"))
        self.PurgeTempOnStartupCheckBox.setToolTip(t("settings.general.advanced.purge_temp_tooltip"))
        self.PurgeTempOnStartupCheckBox.setChecked(get_purge_temp_on_startup())
        self.PurgeTempOnStartupCheckBox.clicked.connect(set_purge_temp_on_startup)

        # Purge Temp Now Button
        self.PurgeTempNowButton = QPushButton(t("settings.general.advanced.purge_temp_now"))
        self.PurgeTempNowButton.setToolTip(t("settings.general.advanced.purge_temp_now_tooltip"))
        self.PurgeTempNowButton.clicked.connect(self.purge_temp_now)

        self.advanced_layout = QGridLayout()
        self.advanced_layout.addWidget(QLabel("Default Delete Action"), 0, 0, 1, 1)
        self.advanced_layout.addWidget(self.default_delete_action, 0, 1, 1, 1)
        self.advanced_layout.addWidget(self.PurgeTempOnStartupCheckBox, 1, 0, 1, 2)
        self.advanced_layout.addWidget(self.PurgeTempNowButton, 2, 0, 1, 2)
        self.advanced_settings.setLayout(self.advanced_layout)
        self.addRow(self.advanced_settings)

    def prompt_library_folder(self):
        library_folder = str(get_library_folder())
        new_library_folder = FileDialogWindow().get_directory(self, t("msg.popup.select_library"), library_folder)
        if new_library_folder and (library_folder != new_library_folder):
            self.set_library_folder(Path(new_library_folder))

    def set_library_folder_(self, p: Path):
        print("SETTTE", p)
        set_library_folder(str(p))

    def library_folder_validity_changed(self, v: bool):
        if not v:
            self.dlg = Popup.warning(
                message=t("msg.err.library_no_write"),
                buttons=Popup.Button.QUIT,
                parent=self.launcher,
            )
            self.dlg.accepted.connect(self.LibraryFolder.button.clicked.emit)

    def toggle_launch_minimized_to_tray(self, is_checked):
        set_launch_minimized_to_tray(is_checked)

    def toggle_show_tray_icon(self, is_checked):
        set_show_tray_icon(is_checked)
        self.LaunchMinimizedToTrayCheckBox.setEnabled(is_checked)
        self.launcher.tray_icon.setVisible(is_checked)

    def set_worker_thread_count(self):
        set_worker_thread_count(self.WorkerThreadCount.value())

    def set_launch_timer_duration(self):
        sfx = t(f"general.file_assoc.launch_timer_suffix.{self.launch_timer_duration.value()}")
        self.launch_timer_duration.setSuffix(sfx)
        set_launch_timer_duration(self.launch_timer_duration.value())

    def migrate_confirmation(self):
        if user_config().exists():
            dlg = Popup.warning(
                message=t("msg.popup.mv_overwrite_confirm", start=get_config_file(), end=user_config()),
                buttons=[Popup.Button.OVERWRITE, Popup.Button.CANCEL],
                parent=self.launcher,
            )
        else:
            dlg = Popup.info(
                message=t("msg.popup.mv_confirm", start=get_config_file(), end=user_config()),
                buttons=[Popup.Button.MIGRATE, Popup.Button.CANCEL],
                parent=self.launcher,
            )

        dlg.accepted.connect(self.migrate)

    def migrate(self):
        migrate_config(force=True)
        self.migrate_button.hide()
        # Most getters should get the settings from the new position, so a restart should not be required

    def create_shortcut(self):
        destination = get_default_program_shortcut_destination()
        file_place = FileDialogWindow().get_save_filename(
            parent=self, title=t("msg.popup.dest"), directory=str(destination)
        )
        if file_place[0]:
            generate_program_shortcut(Path(file_place[0]))

    def refresh_association_buttons(self):
        from modules.shortcut import association_is_registered

        if association_is_registered():
            self.register_file_association_button.setEnabled(False)
            self.unregister_file_association_button.setEnabled(True)
        else:
            self.register_file_association_button.setEnabled(True)
            self.unregister_file_association_button.setEnabled(False)

    def change_default_delete_action(self, index: int):
        action = self.default_delete_action.itemText(index)
        set_default_delete_action(action)

    def toggle_purge_temp_on_startup(self, is_checked):
        set_purge_temp_on_startup(is_checked)

    def purge_temp_now(self):
        success = purge_temp_folder()
        if success:
            Popup.success(
                message=t("msg.popup.purge.success"),
                parent=self.launcher,
            )
        else:
            Popup.error(
                message=t("msg.popup.purge.error"),
                parent=self.launcher,
            )

    def register_with_winget(self):
        success = register_with_winget(sys.executable, str(self.launcher.version))
        if success:
            set_auto_register_winget(True)
            self.refresh_winget_buttons()
            Popup.success(
                message=t("msg.popup.winget.register.success"),
                parent=self.launcher,
            )
        else:
            Popup.error(
                message=t("msg.popup.winget.register.error"),
                parent=self.launcher,
            )

    def unregister_from_winget(self):
        success = unregister_from_winget()
        if success:
            set_auto_register_winget(False)
            self.refresh_winget_buttons()
            Popup.success(
                message=t("msg.popup.winget.unregister.success"),
                parent=self.launcher,
            )
        else:
            Popup.error(
                message=t("msg.popup.winget.unregister.error"),
                parent=self.launcher,
            )

    def refresh_winget_buttons(self):
        if get_platform() != "Windows":
            return

        from modules.winget_integration import is_registered_with_winget

        if is_registered_with_winget():
            self.register_winget_button.setEnabled(False)
            self.unregister_winget_button.setEnabled(True)
        else:
            self.register_winget_button.setEnabled(True)
            self.unregister_winget_button.setEnabled(False)
