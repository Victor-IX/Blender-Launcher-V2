from __future__ import annotations

import os
import sys
from pathlib import Path

from modules._platform import is_frozen
from modules.settings import (
    get_actual_library_folder,
    get_config_file,
    get_cwd,
    get_launch_minimized_to_tray,
    get_launch_timer_duration,
    get_launch_when_system_starts,
    get_library_folder,
    get_platform,
    get_show_tray_icon,
    get_use_pre_release_builds,
    get_worker_thread_count,
    migrate_config,
    set_launch_minimized_to_tray,
    set_launch_timer_duration,
    set_launch_when_system_starts,
    set_library_folder,
    set_show_tray_icon,
    set_use_pre_release_builds,
    set_worker_thread_count,
    user_config,
)
from modules.shortcut import generate_program_shortcut, get_default_shortcut_destination, get_shortcut_type
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QWidget
from widgets.settings_form_widget import SettingsFormWidget
from widgets.settings_window.settings_group import SettingsGroup
from windows.dialog_window import DialogWindow
from windows.file_dialog_window import FileDialogWindow


class GeneralTabWidget(SettingsFormWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        # Library Folder
        self.LibraryFolderLineEdit = QLineEdit()
        self.LibraryFolderLineEdit.setText(str(get_actual_library_folder()))
        self.LibraryFolderLineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.LibraryFolderLineEdit.setReadOnly(True)
        self.LibraryFolderLineEdit.setCursorPosition(0)
        self.SetLibraryFolderButton = QPushButton(self.parent.icons.folder, "")
        self.SetLibraryFolderButton.clicked.connect(self.prompt_library_folder)

        self.LibraryFolderWidget = QWidget()
        self.LibraryFolderLayout = QHBoxLayout(self.LibraryFolderWidget)
        self.LibraryFolderLayout.setContentsMargins(6, 0, 6, 0)
        self.LibraryFolderLayout.setSpacing(0)

        self.LibraryFolderLayout.addWidget(self.LibraryFolderLineEdit)
        self.LibraryFolderLayout.addWidget(self.SetLibraryFolderButton)

        # Launch When System Starts
        self.LaunchWhenSystemStartsCheckBox = QCheckBox()
        self.LaunchWhenSystemStartsCheckBox.setChecked(get_launch_when_system_starts())
        self.LaunchWhenSystemStartsCheckBox.clicked.connect(self.toggle_launch_when_system_starts)

        # Launch Minimized To Tray
        self.LaunchMinimizedToTrayCheckBox = QCheckBox()
        self.LaunchMinimizedToTrayCheckBox.setChecked(get_launch_minimized_to_tray())
        self.LaunchMinimizedToTrayCheckBox.clicked.connect(self.toggle_launch_minimized_to_tray)

        # Show Tray Icon
        self.ShowTrayIconCheckBox = QCheckBox()
        self.ShowTrayIconCheckBox.setChecked(get_show_tray_icon())
        self.ShowTrayIconCheckBox.clicked.connect(self.toggle_show_tray_icon)

        # Worker thread count
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
                    self.WorkerThreadCount.setSuffix(None)

            self.WorkerThreadCount.valueChanged.connect(warn_values_above_cpu)

        # Pre-release builds
        self.PreReleaseBuildsCheckBox = QCheckBox()
        self.PreReleaseBuildsCheckBox.setChecked(get_use_pre_release_builds())
        self.PreReleaseBuildsCheckBox.clicked.connect(self.toggle_use_pre_release_builds)

        # Layout
        self._addRow("Library Folder", self.LibraryFolderWidget, new_line=True)

        if get_platform() == "Windows":
            self._addRow("Launch When System Starts", self.LaunchWhenSystemStartsCheckBox)

        self._addRow("Show Tray Icon", self.ShowTrayIconCheckBox)
        self.LaunchMinimizedToTrayRow = self._addRow("Launch Minimized To Tray", self.LaunchMinimizedToTrayCheckBox)
        self.LaunchMinimizedToTrayRow.setEnabled(get_show_tray_icon())

        self._addRow("Worker Thread Count", self.WorkerThreadCount)

        self._addRow("Use Pre-release Builds", self.PreReleaseBuildsCheckBox)

        if get_config_file() != user_config():
            self.migrate_button = QPushButton("Migrate local settings to user settings", self)
            self.migrate_button.setProperty("CollapseButton", True)
            self.migrate_button.clicked.connect(self.migrate_confirmation)

            self.addRow(self.migrate_button)

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
            self.unregister_file_association_button = QPushButton(
                "Unregister File Association", parent=self.file_association_group
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
            "Determines how much time you have while opening blendfiles to change the build you're launching"
        )
        self.launch_timer_duration.setRange(-1, 120)
        self.launch_timer_duration.setValue(get_launch_timer_duration())
        self.launch_timer_duration.valueChanged.connect(self.set_launch_timer_duration)
        self.set_launch_timer_duration()
        layout.addWidget(QLabel("Launch Timer Duration (secs)"), 2, 0, 1, 1)
        layout.addWidget(self.launch_timer_duration, 2, 1, 1, 1)

        self.file_association_group.setLayout(layout)
        self.addRow(self.file_association_group)

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
        self.LaunchMinimizedToTrayRow.setEnabled(is_checked)
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
        text = f"Are you sure you want to move<br>{get_config_file()}<br>to<br>{user_config()}?"
        if user_config().exists():
            text = f'<font color="red">WARNING:</font> The user settings already exist!<br>{text}'
        dlg = DialogWindow(text=text, parent=self.parent)
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
