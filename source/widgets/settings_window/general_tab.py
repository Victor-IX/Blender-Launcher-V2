from __future__ import annotations

import os
from pathlib import Path

from modules.settings import (
    get_actual_library_folder,
    get_config_file,
    get_cwd,
    get_launch_minimized_to_tray,
    get_launch_when_system_starts,
    get_library_folder,
    get_platform,
    get_show_tray_icon,
    get_use_pre_release_builds,
    get_blender_preferences_management,
    get_worker_thread_count,
    migrate_config,
    set_launch_minimized_to_tray,
    set_launch_when_system_starts,
    set_library_folder,
    set_show_tray_icon,
    set_use_pre_release_builds,
    set_blender_preferences_management,
    set_worker_thread_count,
    user_config,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QLineEdit, QPushButton, QSpinBox, QGridLayout, QLabel, QHBoxLayout
from widgets.settings_form_widget import SettingsFormWidget
from windows.dialog_window import DialogWindow
from windows.file_dialog_window import FileDialogWindow

from .settings_group import SettingsGroup


class GeneralTabWidget(SettingsFormWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent

        # Application Settings
        self.application_settings = SettingsGroup("Application", parent=self)
        
        # Library Folder
        self.LibraryFolderLayoutLabel = QLabel()
        self.LibraryFolderLayoutLabel.setText("Library Folder:")
        self.LibraryFolderLineEdit = QLineEdit()
        self.LibraryFolderLineEdit.setText(str(get_actual_library_folder()))
        self.LibraryFolderLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.LibraryFolderLineEdit.setReadOnly(True)
        self.LibraryFolderLineEdit.setCursorPosition(0)
        self.SetLibraryFolderButton = QPushButton(self.parent.icons.folder, "")
        self.SetLibraryFolderButton.setFixedWidth(25)
        self.SetLibraryFolderButton.clicked.connect(self.prompt_library_folder)
        self.SetLibraryFolderButton.clicked.connect(self.prompt_library_folder)

        self.LibraryFolderLayout = QHBoxLayout()
        self.LibraryFolderLayout.setSpacing(0)
        self.LibraryFolderLayout.addWidget(self.LibraryFolderLineEdit)
        self.LibraryFolderLayout.addWidget(self.SetLibraryFolderButton)

        # Launch When System Starts
        self.LaunchWhenSystemStartsCheckBox = QCheckBox()
        self.LaunchWhenSystemStartsCheckBox.setText("Launch When System Starts")
        self.LaunchWhenSystemStartsCheckBox.setChecked(get_launch_when_system_starts())
        self.LaunchWhenSystemStartsCheckBox.clicked.connect(self.toggle_launch_when_system_starts)

        # Launch Minimized To Tray
        self.LaunchMinimizedToTrayCheckBox = QCheckBox()
        self.LaunchMinimizedToTrayCheckBox.setText("Launch Minimized To Tray")
        self.LaunchMinimizedToTrayCheckBox.setChecked(get_launch_minimized_to_tray())
        self.LaunchMinimizedToTrayCheckBox.clicked.connect(self.toggle_launch_minimized_to_tray)

        # Show Tray Icon
        self.ShowTrayIconCheckBox = QCheckBox()
        self.ShowTrayIconCheckBox.setText("Show Tray Icon")
        self.ShowTrayIconCheckBox.setChecked(get_show_tray_icon())
        self.ShowTrayIconCheckBox.clicked.connect(self.toggle_show_tray_icon)

        # Worker thread count
        self.WorkerThreadCountBox = QLabel()
        self.WorkerThreadCountBox.setText("Worker Thread Count")
        self.WorkerThreadCount = QSpinBox()
        self.WorkerThreadCount.setToolTip(
            "Determines how many IO operations can be done at once, ex. Downloading, deleting, and extracting files"
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

        # Layout
        self.application_layout = QGridLayout()
        self.application_layout.addWidget(self.LibraryFolderLayoutLabel, 0, 0, 1, 1)
        self.application_layout.addLayout(self.LibraryFolderLayout, 1, 0, 1, 3)
        if get_platform() == "Windows":
            self.application_layout.addWidget(self.LaunchWhenSystemStartsCheckBox, 2, 0, 1, 1)
        self.application_layout.addWidget(self.ShowTrayIconCheckBox, 3, 0, 1, 1)
        self.application_layout.addWidget(self.LaunchMinimizedToTrayCheckBox, 4, 0, 1, 1)
        self.application_layout.addWidget(self.WorkerThreadCountBox, 5, 0, 1, 1)
        self.application_layout.addWidget(self.WorkerThreadCount, 5, 1, 1, 2)
        self.application_layout.addWidget(self.PreReleaseBuildsCheckBox, 6, 0, 1, 1)
        self.application_settings.setLayout(self.application_layout)

        # Advence Options Settings
        self.advanced_settings = SettingsGroup("Advanced", parent=self)
        
        # Show Preference Menu
        self.BlenderPreferencesMenuCheckBox = QCheckBox()
        self.BlenderPreferencesMenuCheckBox.setText("Show Blender Preference Menu")
        self.BlenderPreferencesMenuCheckBox.setChecked(get_blender_preferences_management())
        self.BlenderPreferencesMenuCheckBox.clicked.connect(self.toggle_blender_preferences_management)

        # Layout
        self.advanced_layout = QGridLayout()
        self.advanced_layout.addWidget(self.BlenderPreferencesMenuCheckBox, 0, 0, 1, 1)
        self.advanced_settings.setLayout(self.advanced_layout)

        self.addRow(self.application_settings)
        self.addRow(self.advanced_settings)

        if get_config_file() != user_config():
            self.migrate_button = QPushButton("Migrate local settings to user settings", self)
            self.migrate_button.setProperty("CollapseButton", True)
            self.migrate_button.clicked.connect(self.migrate_confirmation)

            self.addRow(self.migrate_button)

    def prompt_library_folder(self):
        library_folder = str(get_library_folder())
        new_library_folder = FileDialogWindow().get_directory(self, "Select Library Folder", library_folder)
        if new_library_folder and (library_folder != new_library_folder):
            self.set_library_folder(Path(new_library_folder))

    def set_library_folder(self, folder: Path, relative: bool | None = None):
        if folder.is_relative_to(get_cwd()):
            if relative is None:
                self.dlg = DialogWindow(
                    parent=self.parent,
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
            self.LibraryFolderLineEdit.setText(str(get_actual_library_folder()))
            self.parent.draw_library(clear=True)
        else:
            self.dlg = DialogWindow(
                parent=self.parent,
                title="Warning",
                text="Selected folder doesn't have write permissions!",
                accept_text="Retry",
                cancel_text=None,
            )
            self.dlg.accepted.connect(self.prompt_library_folder)

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

    def toggle_use_pre_release_builds(self, is_checked):
        set_use_pre_release_builds(is_checked)

    def toggle_blender_preferences_management(self, is_checked):
        set_blender_preferences_management(is_checked)

    def migrate_confirmation(self):
        text = f"Are you sure you want to move<br>{get_config_file()}<br>to<br>{user_config()}?"
        if user_config().exists():
            text = f'<font color="red">WARNING:</font> The user settings already exist!<br>{text}'
        dlg = DialogWindow(text=text, parent=self.parent)
        dlg.accepted.connect(self.migrate)

    def migrate(self):
        migrate_config(force=True)
        self.migrate_button.hide()
        # Most getters should get the settings from the new position, so a restart should not be required
