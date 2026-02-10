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
        with self.group("settings.general.app.label") as grp:
            # Library Folder
            grp.add_label("settings.general.app.library_folder")
            self.LibraryFolder = grp.add(FolderSelector(parent, default_folder=get_actual_library_folder()))
            self.LibraryFolder.validity_changed.connect(self.library_folder_validity_changed)
            self.LibraryFolder.folder_changed.connect(self.set_library_folder_)

            # Launch When System Starts
            if get_platform() == "Windows":
                grp.add_checkbox(
                    "settings.general.app.system_start",
                    default=get_launch_when_system_starts(),
                    setter=set_launch_when_system_starts,
                )

            # Show Tray Icon
            grp.add_checkbox(
                "settings.general.app.minimize",
                default=get_show_tray_icon(),
                setter=self.toggle_show_tray_icon,
            )

            # Launch Minimized To Tray
            self.LaunchMinimizedToTrayCheckBox = grp.add_checkbox(
                "settings.general.app.launch_minimized",
                default=get_launch_minimized_to_tray(),
                setter=set_launch_minimized_to_tray,
            )
            self.LaunchMinimizedToTrayCheckBox.setEnabled(get_launch_when_system_starts())

            # Worker thread count
            spin = grp.add_spin(
                "settings.general.app.worker_count",
                default=get_worker_thread_count(),
                setter=set_worker_thread_count,
                min_=1,
            )

            # Warn if thread count exceeds cpu count
            cpu_count = os.cpu_count()
            if cpu_count is not None:

                def warn_cpu_count(v: int):
                    if v > cpu_count:
                        spin.setSuffix(t("settings.general.app.worker_count_warning"))
                    else:
                        spin.setSuffix("")

                spin.valueChanged.connect(warn_cpu_count)

            # Pre-release builds
            grp.add_checkbox(
                "settings.general.app.prerelease",
                default=get_use_pre_release_builds(),
                setter=set_use_pre_release_builds,
            )

            # Create Shortcut
            grp.add_button(
                "settings.general.app.create_shortcut",
                clicked=self.create_shortcut,
                label_kwargs={
                    "shortcut_type": t(
                        f"settings.general.app.shortcut_type.{get_platform().lower()}",
                    )
                },
            )

        if get_config_file() != user_config():
            self.migrate_button = QPushButton(t("settings.general.migratel2u"), self)
            self.migrate_button.setProperty("CollapseButton", True)
            self.migrate_button.clicked.connect(self.migrate_confirmation)

            self.addRow(self.migrate_button)

        # File Association
        with self.group("settings.general.file_assoc.label") as grp:
            if sys.platform == "win32":
                from modules.shortcut import register_windows_filetypes, unregister_windows_filetypes

                self.register_file_association_button = grp.add_button(
                    "settings.general.file_assoc.register",
                    clicked=register_windows_filetypes,
                )
                self.unregister_file_association_button = grp.add_button(
                    "settings.general.file_assoc.unregister",
                    clicked=unregister_windows_filetypes,
                )
                self.register_file_association_button.clicked.connect(self.refresh_association_buttons)
                self.unregister_file_association_button.clicked.connect(self.refresh_association_buttons)
                self.refresh_association_buttons()

            self.launch_timer_duration = grp.add_spin(
                "settings.general.file_assoc.launch_timer_duration",
                default=get_launch_timer_duration(),
                setter=self.set_launch_timer_duration,
                min_=-1,
            )
            self.set_launch_timer_duration(get_launch_timer_duration())

        # WinGet Integration
        if get_platform() == "Windows":
            with self.group("settings.general.winget.label") as grp:
                lbl = grp.add_label("settings.general.winget.label")
                lbl.setWordWrap(True)

                self.register_winget_button = grp.add_button(
                    "settings.general.winget.register",
                    clicked=self.register_with_winget,
                )
                self.unregister_winget_button = grp.add_button(
                    "settings.general.winget.unregister",
                    clicked=self.unregister_from_winget,
                )
                self.refresh_winget_buttons()

        with self.group("settings.general.advanced.label") as grp:
            grp.add_label("settings.general.advanced.default_delete_action")
            # Default Deletion Action
            self.default_delete_action = grp.add(QComboBox())
            self.default_delete_action.addItems(delete_action.keys())
            self.default_delete_action.setToolTip(t("settings.general.advanced.default_delete_action_tooltip"))
            self.default_delete_action.setCurrentIndex(get_default_delete_action())
            self.default_delete_action.activated[int].connect(self.change_default_delete_action)

            # Purge Temp on Startup
            grp.add_checkbox(
                "settings.general.advanced.purge_temp",
                default=get_purge_temp_on_startup(),
                setter=set_purge_temp_on_startup,
            )
            # Purge Temp Now
            grp.add_button("settings.general.advanced.purge_temp_now", clicked=self.purge_temp_now)

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

    def set_launch_timer_duration(self, val: int):
        if val <= 0:
            v = val
        else:
            v = "more"
        sfx = t(f"settings.general.file_assoc.launch_timer_suffix.{v}")
        self.launch_timer_duration.setSuffix(sfx)
        set_launch_timer_duration(val)

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
