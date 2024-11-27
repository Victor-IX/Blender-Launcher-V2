from __future__ import annotations

import contextlib
import shutil
import sys
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from modules._platform import get_cwd, get_platform, is_frozen
from modules.settings import (
    get_actual_library_folder,
    get_actual_library_folder_no_fallback,
    get_enable_high_dpi_scaling,
    get_scrape_automated_builds,
    get_scrape_stable_builds,
    get_show_tray_icon,
    get_use_system_titlebar,
    set_enable_high_dpi_scaling,
    set_library_folder,
    set_scrape_automated_builds,
    set_scrape_bfa_builds,
    set_scrape_stable_builds,
    set_show_bfa_builds,
    set_show_daily_builds,
    set_show_experimental_and_patch_builds,
    set_show_stable_builds,
    set_show_tray_icon,
    set_use_system_titlebar,
)
from modules.shortcut import generate_program_shortcut, get_default_shortcut_destination, register_windows_filetypes
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)
from widgets.folder_select import FolderSelector
from widgets.repo_group import RepoGroup
from windows.dialog_window import DialogWindow
from windows.file_dialog_window import FileDialogWindow

if TYPE_CHECKING:
    from semver import Version
    from windows.main_window import BlenderLauncher


@dataclass
class PropogatedSettings:
    exe_location: Path = field(default=Path(sys.executable))
    exe_changed: bool = False

class BasicOnboardingPage(QWizardPage):
    def __init__(self, prop_settings: PropogatedSettings, parent=None):
        super().__init__(parent=parent)
        self.prop_settings = prop_settings

    @abstractmethod
    def evaluate(self):
        """Runs the settings and make sure everything is set up correctly before BLV2 init"""
        raise NotImplementedError


class WelcomePage(BasicOnboardingPage):
    def __init__(self, v: Version, prop_settings: PropogatedSettings, parent=None):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(f"Welcome to Blender Launcher v{v}!")
        self.layout_ = QHBoxLayout(self)

        self.label = QLabel(
            "In this First-Time Setup, we will walk through the most common settings you will likely want to configure.<br>\
                you only have to do this once and never again.<br>\
                All of these settings can be changed in the future."
        )
        self.label.setWordWrap(True)
        font = self.label.font()
        font.setPointSize(14)
        self.label.setFont(font)

        self.layout_.addWidget(self.label)

    def evaluate(self): ...


class ChooseLibraryPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("First, choose where Blender builds will be stored")
        self.setSubTitle("Make sure that this folder has enough storage to download and store all the builds you want.")

        self.lf = FolderSelector(
            parent,
            default_folder=get_actual_library_folder_no_fallback() or Path("~/Documents/BlenderBuilds").expanduser(),
            default_choose_dir_folder=get_actual_library_folder(),
            parent=self,
        )
        self.move_exe = QCheckBox("Move exe to library", parent=self)
        self.move_exe.setToolTip(
            "Moves the program's exe to the specified location. Once first-time-setup is complete, you'll have to refer to this location in subsequent runs."
        )
        self.move_exe.setChecked(True)
        self.move_exe.setVisible(is_frozen())  # hide when exe is not frozen

        self.layout_ = QVBoxLayout(self)
        self.layout_.addWidget(QLabel("Library location:", self))
        self.layout_.addWidget(self.lf)
        self.layout_.addWidget(self.move_exe)

        self.lf.validity_changed.connect(self.completeChanged)

    def isComplete(self) -> bool:
        return self.lf.is_valid

    def evaluate(self):
        pth = Path(self.lf.line_edit.text())

        set_library_folder(str(pth))

        if is_frozen() and self.move_exe.isChecked():  # move the executable to the library location
            exe = pth / self.prop_settings.exe_location.name
            self.prop_settings.exe_location = exe
            self.prop_settings.exe_changed = True
            exe.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(sys.executable, exe)
            Path(sys.executable).unlink()


class RepoSelectPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Choose which repositories you want enabled")
        self.setSubTitle("This will enable/disable certain builds of blender to be visible / scraped.")
        self.layout_ = QVBoxLayout(self)

        self.group = RepoGroup(self)
        self.layout_.addWidget(self.group)

    def evaluate(self):
        set_show_stable_builds(self.group.stable_repo.library)
        set_show_daily_builds(self.group.daily_repo.library)
        set_show_experimental_and_patch_builds(self.group.experimental_repo.library)
        set_show_bfa_builds(self.group.bforartists_repo.library)

        set_scrape_stable_builds(self.group.stable_repo.download)
        set_scrape_automated_builds(self.group.daily_repo.download)
        set_scrape_bfa_builds(self.group.bforartists_repo.download)


class ShortcutsPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Shortcuts / Launching Blendfiles (.blend, .blend1)")
        subtitle = 'This will allow you to automatically launch the correct version for a file\
 using the "Open With.." functionality on your desktop.'
        self.setSubTitle(subtitle)

        self.layout_ = QVBoxLayout(self)
        explanation = ""
        self.platform = get_platform()
        self.explanation_label = QLabel(self)
        if self.platform == "Windows":  # Give a subtitle relating to the registry
            explanation = """In order to do this on Windows, we will update the registry to relate the launcher to the .blend extension.
To reverse this after installation, there is a labeled panel in the Settings general tab. You will find a button to unregister the launcher there.

Hover over this text to see which registry keys will be changed, and for what reason.
"""
            self.explanation_label.setToolTip(r"""The Following keys will be changed:
CREATE Software\Classes\blenderlauncherv2.blend\shell\open\command -- To expose the launcher as a software class
UPDATE Software\Classes\.blend\OpenWithProgids -- To add the launcher to the .blend "Open With.." list
UPDATE Software\Classes\.blend1\OpenWithProgids -- To add the launcher to the .blend1 "Open With.." list
CREATE Software\Classes\blenderlauncherv2.blend\DefaultIcon -- To set the icon when BLV2 is the default application
These will be deleted/downgraded when you unregister the launcher""")
        if self.platform == "Linux":
            explanation = """In order to do this on Linux, we will generate a .desktop file at the requested location.\
 It contains mimetype data which tells the desktop environment (DE) what files the program expects to handle, and as a side effect the program is also visible in application launchers.

Our default location is typically searched by DEs for application entries.
"""
        self.explanation_label.setText(explanation)
        self.explanation_label.setWordWrap(True)
        self.layout_.addWidget(self.explanation_label)

        self.use_file_associations = QCheckBox("Register for file associations", parent=self)
        self.layout_.addWidget(self.use_file_associations)

        self.select: FolderSelector | None = None
        if self.platform == "Linux":
            self.select = FolderSelector(
                parent,
                default_folder=get_default_shortcut_destination().parent,
                check_relatives=False,
            )
            self.select.setEnabled(False)
            self.use_file_associations.toggled.connect(self.select.setEnabled)
            self.layout_.addWidget(self.select)
        elif self.platform == "Windows":
            self.layout_.addSpacerItem(None)
            self.addtostart = QCheckBox("Add to Start Menu", parent=self)
            self.addtostart.setChecked(False)
            self.addtodesk = QCheckBox("Add to Desktop", parent=self)
            self.addtodesk.setChecked(False)

            self.layout_.addWidget(self.addtostart)
            self.layout_.addWidget(self.addtodesk)

    def evaluate(self):
        if self.use_file_associations.isChecked():
            if self.select is not None:  # then we should make a desktop file
                assert self.select.path is not None

                if self.select.path.is_dir():
                    pth = self.select.path / get_default_shortcut_destination().name
                else:
                    pth = self.select.path

                generate_program_shortcut(pth, exe=str(self.prop_settings.exe_location))
                return

            if self.platform == "Windows":
                register_windows_filetypes(exe=str(self.prop_settings.exe_location))

        elif self.platform == "Windows":
            if self.addtostart.isChecked():
                generate_program_shortcut(
                    get_default_shortcut_destination(), exe=str(self.prop_settings.exe_location)
                )
            if self.addtodesk.isChecked():
                generate_program_shortcut(
                    Path("~/Desktop/Blender Launcher V2").expanduser(), exe=str(self.prop_settings.exe_location)
                )


class AppearancePage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("BLV2 appearance")
        self.setSubTitle("Configure how BLV2 Looks")
        self.layout_ = QVBoxLayout(self)

        self.titlebar = QCheckBox("Use System Titlebar", self)
        self.titlebar.setChecked(get_use_system_titlebar())
        titlebar_label = QLabel(
            """This disables the custom title bar and uses the OS's default titlebar.

In Linux Wayland environments, this is recommended because you will be
able to use the title for moving and resizing the windows.
Our main method of moving and resizing works best on X11.""",
            self,
        )
        self.highdpiscaling = QCheckBox("High DPI Scaling")
        self.highdpiscaling.setChecked(get_enable_high_dpi_scaling())
        highdpiscaling_label = QLabel(
            """


This enables high DPI scaling for the program.
automatically scales the user interface based on the monitor's pixel density."""
        )

        self.layout_.addWidget(titlebar_label)
        self.layout_.addWidget(self.titlebar)
        self.layout_.addWidget(highdpiscaling_label)
        self.layout_.addWidget(self.highdpiscaling)

    def evaluate(self):
        set_use_system_titlebar(self.titlebar.isChecked())
        set_enable_high_dpi_scaling(self.highdpiscaling.isChecked())


class BackgroundRunningPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Running BLV2 in the background")
        self.setSubTitle("""BLV2 can be kept alive in the background with a system tray icon.\
 This can be useful for reading efficiency and other features, but it is not totally necessary.""")
        self.layout_ = QVBoxLayout(self)

        self.enable_btn = QCheckBox("Run BLV2 in the background (Minimise to tray)")
        self.enable_btn.setChecked(get_show_tray_icon())
        self.layout_.addWidget(self.enable_btn)

    def evaluate(self):
        set_show_tray_icon(self.enable_btn.isChecked())


class CommittingPage(QWizardPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle("Committing settings changes...")
        self.setSubTitle("This should take less than a second.")


class ErrorOccurredPage(QWizardPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle("An Error occured during setup!")
        self.layout_ = QVBoxLayout(self)
        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.layout_.addWidget(self.output)
        self.layout_.addWidget(QLabel("Continue anyways?", self))
