from __future__ import annotations

import shutil
import sys
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from modules._platform import get_platform, is_frozen
from modules.settings import (
    get_actual_library_folder,
    get_actual_library_folder_no_fallback,
    get_enable_high_dpi_scaling,
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
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWizardPage,
)
from widgets.folder_select import FolderSelector
from widgets.repo_group import RepoGroup

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


WELCOME_TEXT = """
In this First-Time Setup, we will walk through the most common settings you will likely want to configure.
you only have to do this once and never again.
All of these settings can be changed in the future.
"""


class WelcomePage(BasicOnboardingPage):
    def __init__(self, v: Version, prop_settings: PropogatedSettings, parent=None):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(f"Welcome to Blender Launcher v{v}!")
        self.layout_ = QHBoxLayout(self)

        self.label = QLabel(WELCOME_TEXT)
        self.label.setWordWrap(True)
        font = self.label.font()
        font.setPointSize(14)
        self.label.setFont(font)

        self.layout_.addWidget(self.label)

    def evaluate(self): ...


PERM_WARNING_LABEL_WINDOWS = (
    "Warning: Do not use C:/Program Files/... as your library location or anywhere else you may not have permissions"
)
PERM_WARNING_LABEL_LINUX = (
    "Warning: Do not use /bin as your library location or anywhere else you may not have permissions"
)


class ChooseLibraryPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Blender Launcher library location")
        self.setSubTitle("Make sure that this folder has enough storage to download and store all the builds you want.")
        self.launcher = parent
        self.lf = FolderSelector(
            parent,
            default_folder=get_actual_library_folder_no_fallback() or Path("~/Documents/BlenderBuilds").expanduser(),
            default_choose_dir_folder=get_actual_library_folder(),
            parent=self,
        )
        
        home = Path().home()
        executable_path = Path(sys.executable)
 
        self.move_exe = QCheckBox("Move exe to library", parent=self)
        self.move_exe.setToolTip(
            "Moves the program's exe to the specified location. Once first-time-setup is complete, you'll have to refer to this location in subsequent runs."
        )

        self.move_exe.setChecked(home in executable_path.parents)
        self.move_exe.setVisible(is_frozen())  # hide when exe is not frozen

        self.warning_label = QLabel(self)
        if get_platform() == "Windows":
            self.warning_label.setText(PERM_WARNING_LABEL_WINDOWS)
        else:
            self.warning_label.setText(PERM_WARNING_LABEL_LINUX)

        self.warning_label.setWordWrap(True)

        self.layout_ = QVBoxLayout(self)
        self.layout_.addWidget(self.warning_label)
        self.layout_.addWidget(QLabel("Library location:", self))
        self.layout_.addWidget(self.lf)
        if home not in executable_path.parents:
            self.path_warning_label = QLabel(self)
            self.path_warning_label.setText(f"The program's exe is outside of {str(home)}, it may lack the permisisons needed to move the executable to the library!")
            self.path_warning_label.setWordWrap(True)
            self.layout_.addWidget(self.path_warning_label)
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

            if exe.absolute() == sys.executable:
                return

            self.prop_settings.exe_changed = True
            exe.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(sys.executable, exe)
            if get_platform() == "Windows":  # delete the exe when closed
                # self.launcher.delete_exe_on_reboot = True
                ...
            else:  # delete the executable directly
                Path(sys.executable).unlink()


class RepoSelectPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Blender repositories visibility")
        self.setSubTitle("Enable/disable certain builds of blender to be visible/scraped.")
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


ASSOC_WINDOWS_EXPLAIN = """In order to launch blendfiles with Blender Launcher on Windows, we will update the registry to relate the launcher to the .blend extension. \
To reverse this after installation, there is a labeled panel in the Settings general tab. You will find a button to unregister the launcher there.

Hover over this text to see which registry keys will be changed and for what reason.
"""

ASSOC_LINUX_EXPLAIN = """In order to launch blendilfes with Blender Launcher on Linux, we will generate a .desktop file at the requested location. \
It contains mimetype data which tells the desktop environment (DE) what files the program expects to handle, and as a side effect the program is also visible in application launchers.

Our default location is typically searched by DEs for application entries.
"""


REGISTRY_KEY_EXPLAIN = r"""The Following keys will be changed:
CREATE Software\Classes\blenderlauncherv2.blend\shell\open\command -- To expose the launcher as a software class
UPDATE Software\Classes\.blend\OpenWithProgids -- To add the launcher to the .blend "Open With..." list
CREATE Software\Classes\blenderlauncherv2.blend\DefaultIcon -- To set the icon when Blender Launcher is the default application
These will be deleted/downgraded when you unregister the launcher"""


class ShortcutsPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Shortcuts and file association")
        subtitle = "Create Blender Launcher shortcuts and register file associations to open .blend files directly with Blender Launcher"
        self.setSubTitle(subtitle)

        self.platform = get_platform()
        self.layout_ = QVBoxLayout(self)

        explanation = ""
        self.explanation_label = QLabel(self)
        if self.platform == "Windows":  # Give a subtitle relating to the registry
            explanation = ASSOC_WINDOWS_EXPLAIN
            self.explanation_label.setToolTip(REGISTRY_KEY_EXPLAIN)
        if self.platform == "Linux":
            explanation = ASSOC_LINUX_EXPLAIN
        self.explanation_label.setText(explanation)
        self.explanation_label.setWordWrap(True)

        self.use_file_associations = QCheckBox("Register for file associations", parent=self)

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
            self.addtostart = QCheckBox("Add to Start Menu", parent=self)
            self.addtostart.setChecked(True)
            self.addtodesk = QCheckBox("Add to Desktop", parent=self)
            self.addtodesk.setChecked(True)

            self.layout_.insertWidget(0, self.addtostart)
            self.layout_.insertWidget(1, self.addtodesk)
            self.layout_.insertSpacing(2, 40)

        self.layout_.addWidget(self.use_file_associations)
        self.layout_.addWidget(self.explanation_label)

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
            from win32comext.shell import shell, shellcon

            if self.addtostart.isChecked():
                generate_program_shortcut(
                    get_default_shortcut_destination(),
                    exe=str(self.prop_settings.exe_location),
                )
            if self.addtodesk.isChecked():
                desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, None, 0)

                try:
                    generate_program_shortcut(
                        desktop,
                        exe=str(self.prop_settings.exe_location),
                    )
                except Exception as e:
                    raise Exception(f"Exceptions raised while generating desktop shortcuts: {e}")


TITLEBAR_LABEL_TEXT = """This disables the custom title bar and uses the OS's default titlebar."""
TITLEBAR_LABEL_TEXT_LINUX = """This disables the custom title bar and uses the OS's default titlebar.

In Linux Wayland environments, this is recommended because you will be
able to use the title for moving and resizing the windows.
Our main method of moving and resizing works best on X11."""

TITLEBAR_LABEL_TEXT = """This disables the custom title bar and uses the OS's default titlebar."""

HIGH_DPI_TEXT = """This enables high DPI scaling for the program.
automatically scales the user interface based on the monitor's pixel density."""


class AppearancePage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Blender Launcher appearance")
        self.setSubTitle("Configure how Blender Launcher Looks")
        self.layout_ = QVBoxLayout(self)

        self.titlebar = QCheckBox("Use System Titlebar", self)
        self.titlebar.setChecked(get_use_system_titlebar())
        if get_platform() == "Linux":
            titlebar_label = QLabel(TITLEBAR_LABEL_TEXT_LINUX, self)
        else:
            titlebar_label = QLabel(TITLEBAR_LABEL_TEXT, self)
        self.highdpiscaling = QCheckBox("High DPI Scaling")
        self.highdpiscaling.setChecked(get_enable_high_dpi_scaling())
        highdpiscaling_label = QLabel(HIGH_DPI_TEXT)

        self.layout_.addWidget(titlebar_label)
        self.layout_.addWidget(self.titlebar)
        self.layout_.addWidget(highdpiscaling_label)
        self.layout_.addWidget(self.highdpiscaling)

    def evaluate(self):
        set_use_system_titlebar(self.titlebar.isChecked())
        set_enable_high_dpi_scaling(self.highdpiscaling.isChecked())


BACKGROUND_SUBTITLE = """Blender Launcher can be kept alive in the background with a system tray icon.\
 This can be useful for reading efficiency and other features, but it is not totally necessary."""


class BackgroundRunningPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle("Running Blender Launcher in the background")
        self.setSubTitle(BACKGROUND_SUBTITLE)
        self.layout_ = QVBoxLayout(self)

        self.enable_btn = QCheckBox("Run Blender Launcher in the background (Minimise to tray)")
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
