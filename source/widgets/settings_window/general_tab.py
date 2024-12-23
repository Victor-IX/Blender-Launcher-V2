from __future__ import annotations

import os
import sys
from pathlib import Path
from turtle import title

from modules.settings import (
    get_actual_library_folder,
    get_config_file,
    get_launch_minimized_to_tray,
    get_launch_timer_duration,
    get_launch_when_system_starts,
    get_library_folder,
    get_platform,
    get_show_tray_icon,
    get_use_pre_release_builds,
    get_worker_thread_count,
    get_default_delete_action,
    migrate_config,
    delete_action,
    set_launch_minimized_to_tray,
    set_launch_timer_duration,
    set_launch_when_system_starts,
    set_library_folder,
    set_show_tray_icon,
    set_use_pre_release_builds,
    set_worker_thread_count,
    set_default_delete_action,
    user_config,
)
from modules.shortcut import generate_program_shortcut, get_default_shortcut_destination, get_shortcut_type
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QComboBox,
)
from widgets.folder_select import FolderSelector
from widgets.settings_form_widget import SettingsFormWidget
from widgets.settings_window.settings_group import SettingsGroup
from windows.popup_window import PopupWindow, DialogIcon
from windows.file_dialog_window import FileDialogWindow


class GeneralTabWidget(SettingsFormWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent

        # Application Settings
        self.application_settings = SettingsGroup("Application", parent=self)

        # Library Folder
        self.LibraryFolderLabel = QLabel()
        self.LibraryFolderLabel.setText("Library Folder:")
        self.LibraryFolder = FolderSelector(parent, default_folder=get_actual_library_folder())
        self.LibraryFolder.validity_changed.connect(self.library_folder_validity_changed)
        self.LibraryFolder.folder_changed.connect(self.set_library_folder_)

        # Launch When System Starts
        self.LaunchWhenSystemStartsCheckBox = QCheckBox()
        self.LaunchWhenSystemStartsCheckBox.setText("Launch When System Starts")
        self.LaunchWhenSystemStartsCheckBox.setToolTip(
            "Start the app when the system starts.\
            \nDEFAULT: Off"
        )
        self.LaunchWhenSystemStartsCheckBox.setChecked(get_launch_when_system_starts())
        self.LaunchWhenSystemStartsCheckBox.clicked.connect(self.toggle_launch_when_system_starts)

        # Launch Minimized To Tray
        self.LaunchMinimizedToTrayCheckBox = QCheckBox()
        self.LaunchMinimizedToTrayCheckBox.setText("Launch Minimized To Tray")
        self.LaunchMinimizedToTrayCheckBox.setToolTip(
            "Start the app minimized to the system tray.\
            \nDEFAULT: Off"
        )
        self.LaunchMinimizedToTrayCheckBox.setChecked(get_launch_minimized_to_tray())
        self.LaunchMinimizedToTrayCheckBox.setEnabled(get_launch_when_system_starts())
        self.LaunchMinimizedToTrayCheckBox.clicked.connect(self.toggle_launch_minimized_to_tray)

        # Show Tray Icon
        self.ShowTrayIconCheckBox = QCheckBox()
        self.ShowTrayIconCheckBox.setText("Minimise to tray")
        self.ShowTrayIconCheckBox.setChecked(get_show_tray_icon())
        self.ShowTrayIconCheckBox.clicked.connect(self.toggle_show_tray_icon)
        self.ShowTrayIconCheckBox.setToolTip(
            "Closing the app will minimise it to the system tray instead of closing it completely\
            \nDEFAULT: Off"
        )

        # Worker thread count
        self.WorkerThreadCountBox = QLabel()
        self.WorkerThreadCountBox.setText("Worker Thread Count")
        self.WorkerThreadCount = QSpinBox()
        self.WorkerThreadCount.setToolTip(
            "Determines how many IO operations can be done at once, ex. Downloading, deleting, and extracting files\
            \nDEFAULT: cpu_count * (3/4)"
        )
        self.WorkerThreadCount.editingFinished.connect(self.set_worker_thread_count)
        self.WorkerThreadCount.setMinimum(1)
        self.WorkerThreadCount.setValue(get_worker_thread_count())

        # Warn if thread count exceeds cpu count
        cpu_count = os.cpu_count()
        if cpu_count is not None:

            def warn_values_above_cpu(v: int):
                if v > cpu_count:
                    self.WorkerThreadCount.setSuffix(f" (warning: value above {cpu_count} (cpu count) !!)")
                else:
                    self.WorkerThreadCount.setSuffix("")

            self.WorkerThreadCount.valueChanged.connect(warn_values_above_cpu)

        # Pre-release builds
        self.PreReleaseBuildsCheckBox = QCheckBox()
        self.PreReleaseBuildsCheckBox.setText("Use Pre-release Builds")
        self.PreReleaseBuildsCheckBox.setChecked(get_use_pre_release_builds())
        self.PreReleaseBuildsCheckBox.clicked.connect(self.toggle_use_pre_release_builds)
        self.PreReleaseBuildsCheckBox.setToolTip(
            "While checking for a new version of Blender Launcher, check for pre-releases.\
            \nWARNING: These builds are likely to have bugs! They are mainly used for testing new features.\
            \nDEFAULT: Off"
        )

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
        self.application_settings.setLayout(self.application_layout)

        self.addRow(self.application_settings)

        if get_config_file() != user_config():
            self.migrate_button = QPushButton("Migrate local settings to user settings", self)
            self.migrate_button.setProperty("CollapseButton", True)
            self.migrate_button.clicked.connect(self.migrate_confirmation)

            self.addRow(self.migrate_button)

        # File Association
        self.file_association_group = SettingsGroup("File association", parent=self)
        layout = QGridLayout()
        self.create_shortcut_button = QPushButton(f"Create {get_shortcut_type()}", parent=self.file_association_group)
        self.create_shortcut_button.clicked.connect(self.create_shortcut)
        layout.addWidget(self.create_shortcut_button, 0, 0, 1, 2)

        if sys.platform == "win32":
            from modules.shortcut import register_windows_filetypes, unregister_windows_filetypes

            self.register_file_association_button = QPushButton(
                "Register File Association", parent=self.file_association_group
            )
            self.register_file_association_button.setToolTip(
                "Add Blender Launcher from the list of programs that can open .blend files"
            )

            self.unregister_file_association_button = QPushButton(
                "Unregister File Association", parent=self.file_association_group
            )
            self.unregister_file_association_button.setToolTip(
                "Removes Blender Launcher from the list of programs that can open .blend files"
            )
            self.register_file_association_button.clicked.connect(register_windows_filetypes)
            self.register_file_association_button.clicked.connect(self.refresh_association_buttons)
            self.unregister_file_association_button.clicked.connect(unregister_windows_filetypes)
            self.unregister_file_association_button.clicked.connect(self.refresh_association_buttons)
            self.refresh_association_buttons()
            layout.addWidget(self.register_file_association_button, 1, 0, 1, 1)
            layout.addWidget(self.unregister_file_association_button, 1, 1, 1, 1)

        self.launch_timer_duration = QSpinBox()
        self.launch_timer_duration.setToolTip(
            "Determines how much time you have while opening blendfiles to change the build you're launching\
            \nDEFAULT: 3s"
        )
        self.launch_timer_duration.setRange(-1, 120)
        self.launch_timer_duration.setValue(get_launch_timer_duration())
        self.launch_timer_duration.valueChanged.connect(self.set_launch_timer_duration)
        self.set_launch_timer_duration()
        layout.addWidget(QLabel("Launch Timer Duration (secs)"), 2, 0, 1, 1)
        layout.addWidget(self.launch_timer_duration, 2, 1, 1, 1)

        self.file_association_group.setLayout(layout)
        self.addRow(self.file_association_group)

        self.advanced_settings = SettingsGroup("Advanced", parent=self)
        self.default_delete_action = QComboBox()
        self.default_delete_action.addItems(delete_action.keys())
        self.default_delete_action.setToolTip(
            "Set the default action available in the right click menu for deleting a build\
            \nThe other option is available when holding the shift key\
            \nDEFAULT: Send to Trash"
        )
        self.default_delete_action.setCurrentIndex(get_default_delete_action())
        self.default_delete_action.activated[int].connect(self.change_default_delete_action)

        self.advanced_layout = QGridLayout()
        self.advanced_layout.addWidget(QLabel("Default Delete Action"), 0, 0, 1, 1)
        self.advanced_layout.addWidget(self.default_delete_action, 0, 1, 1, 1)
        self.advanced_settings.setLayout(self.advanced_layout)
        self.addRow(self.advanced_settings)

    def prompt_library_folder(self):
        library_folder = str(get_library_folder())
        new_library_folder = FileDialogWindow().get_directory(self, "Select Library Folder", library_folder)
        if new_library_folder and (library_folder != new_library_folder):
            self.set_library_folder(Path(new_library_folder))

    def set_library_folder_(self, p: Path):
        print("SETTTE", p)
        set_library_folder(str(p))

    def library_folder_validity_changed(self, v: bool):
        if not v:
            self.dlg = PopupWindow(
                parent=self.parent,
                title="Warning",
                message="Selected folder doesn't have write permissions!",
                button="Quit",
            )
            self.dlg.accepted.connect(self.LibraryFolder.button.clicked.emit)

    def toggle_launch_when_system_starts(self, is_checked):
        set_launch_when_system_starts(is_checked)

    def toggle_launch_minimized_to_tray(self, is_checked):
        set_launch_minimized_to_tray(is_checked)

    def toggle_show_tray_icon(self, is_checked):
        set_show_tray_icon(is_checked)
        self.LaunchMinimizedToTrayCheckBox.setEnabled(is_checked)
        self.parent.tray_icon.setVisible(is_checked)

    def set_worker_thread_count(self):
        set_worker_thread_count(self.WorkerThreadCount.value())

    def set_launch_timer_duration(self):
        if self.launch_timer_duration.value() == -1:
            self.launch_timer_duration.setSuffix(" (Disabled)")
        elif self.launch_timer_duration.value() == 0:
            self.launch_timer_duration.setSuffix("s (Immediate)")
        else:
            self.launch_timer_duration.setSuffix("s")
        set_launch_timer_duration(self.launch_timer_duration.value())

    def toggle_use_pre_release_builds(self, is_checked):
        set_use_pre_release_builds(is_checked)

    def migrate_confirmation(self):
        title = "Info"
        text = f"Are you sure you want to move<br>{get_config_file()}<br>to<br>{user_config()}?"
        button = "Migrate, Cancel"
        icon = DialogIcon.NONE
        if user_config().exists():
            title = "Warning"
            text = f'<font color="red">WARNING:</font> The user settings already exist!<br>{text}'
            button = "Overwrite, Cancel"
            icon = DialogIcon.WARNING
        dlg = PopupWindow(title=title, text=text, button=button, icon=icon, parent=self.parent)
        dlg.accepted.connect(self.migrate)

    def migrate(self):
        migrate_config(force=True)
        self.migrate_button.hide()
        # Most getters should get the settings from the new position, so a restart should not be required

    def create_shortcut(self):
        destination = get_default_shortcut_destination()
        file_place = FileDialogWindow().get_save_filename(
            parent=self, title="Choose destination", directory=str(destination)
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
