from __future__ import annotations

import shutil
import sys
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from i18n import t
from modules.platform_utils import find_app_bundle, get_platform, is_frozen
from modules.settings import (
    get_actual_library_folder,
    get_actual_library_folder_no_fallback,
    get_dpi_scale_factor,
    get_show_tray_icon,
    get_use_system_titlebar,
    set_dpi_scale_factor,
    set_library_folder,
    set_scrape_bfa_builds,
    set_scrape_daily_builds,
    set_scrape_experimental_builds,
    set_scrape_stable_builds,
    set_show_bfa_builds,
    set_show_daily_builds,
    set_show_experimental_and_patch_builds,
    set_show_stable_builds,
    set_show_tray_icon,
    set_use_system_titlebar,
)
from modules.shortcut import (
    generate_program_shortcut,
    get_default_program_shortcut_destination,
    get_default_shortcut_folder,
    register_windows_filetypes,
)
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWizardPage
from utils.dpi import DPI_OVERRIDDEN
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


class WelcomePage(BasicOnboardingPage):
    def __init__(self, v: Version, prop_settings: PropogatedSettings, parent=None):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizard.welcome.title", v=v))
        self.layout_ = QHBoxLayout(self)

        self.label = QLabel(t("wizard.welcome.text"))
        self.label.setWordWrap(True)
        font = self.label.font()
        font.setPointSize(14)
        self.label.setFont(font)

        self.layout_.addWidget(self.label)

    def evaluate(self): ...


class ChooseLibraryPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizard.library.title"))
        self.setSubTitle(t("wizard.library.subtitle"))
        self.launcher = parent
        self.lf = FolderSelector(
            parent,
            default_folder=get_actual_library_folder_no_fallback() or Path("~/Documents/BlenderBuilds").expanduser(),
            default_choose_dir_folder=get_actual_library_folder(),
            parent=self,
        )

        # TODO: Remove this when we have a better solution
        # Check if the exe is in the home directory
        # Temp fix to prevent user accidentally moving the exe if BL is downloaded through a package manager
        home = Path().home()
        executable_path = Path(sys.executable)

        self.move_exe = QCheckBox(t("wizard.library.move_exe"), parent=self)
        self.move_exe.setToolTip(t("wizard.library.move_exe_tooltip"))

        self.move_exe.setChecked(home in executable_path.parents)
        self.move_exe.setVisible(is_frozen())  # hide when exe is not frozen

        self.warning_label = QLabel(self)
        if get_platform() == "Windows":
            self.warning_label.setText(t("wizard.library.perm_warning.Windows"))
        else:
            self.warning_label.setText(t("wizard.library.perm_warning.Linux"))

        self.warning_label.setWordWrap(True)

        self.layout_ = QVBoxLayout(self)
        self.layout_.addWidget(self.warning_label)
        self.layout_.addWidget(QLabel(t("wizard.library.location"), self))
        self.layout_.addWidget(self.lf)
        if home not in executable_path.parents:
            self.path_warning_label = QLabel(self)
            self.path_warning_label.setText(t("wizard.library.path_warning", home=str(home)))
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
            platform = get_platform()

            if platform == "macOS":
                # On macOS, we need to move the entire .app bundle
                app_bundle = find_app_bundle(Path(sys.executable))

                if app_bundle is not None:
                    # Move the entire .app bundle
                    dest_app = pth / app_bundle.name

                    if dest_app.exists():
                        return

                    self.prop_settings.exe_changed = True
                    dest_app.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(app_bundle, dest_app)

                    # Update exe_location to point to the executable inside the moved .app
                    # Maintain the same relative path from .app to executable
                    relative_exe = Path(sys.executable).relative_to(app_bundle)
                    self.prop_settings.exe_location = dest_app / relative_exe

                    # Delete the original .app bundle immediately
                    shutil.rmtree(app_bundle)
                    return
                # If no .app bundle found, fall through to move just the executable

            # Windows and Linux, or macOS without .app bundle
            exe = pth / self.prop_settings.exe_location.name
            self.prop_settings.exe_location = exe

            if exe.exists():
                return

            self.prop_settings.exe_changed = True
            exe.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(sys.executable, exe)
            if platform == "Windows":  # delete the exe when closed
                # self.launcher.delete_exe_on_reboot = True
                ...
            else:  # delete the executable directly
                Path(sys.executable).unlink()


class RepoSelectPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizard.repo_select.title"))
        self.setSubTitle(t("wizard.repo_select.subtitle"))
        self.layout_ = QVBoxLayout(self)

        self.group = RepoGroup(self)
        self.layout_.addWidget(self.group)

    def evaluate(self):
        set_show_stable_builds(self.group.stable_repo.library)
        set_show_daily_builds(self.group.daily_repo.library)
        set_show_experimental_and_patch_builds(self.group.experimental_repo.library)
        set_show_bfa_builds(self.group.bforartists_repo.library)

        set_scrape_stable_builds(self.group.stable_repo.download)
        set_scrape_daily_builds(self.group.daily_repo.download)
        set_scrape_experimental_builds(self.group.experimental_repo.download)
        set_scrape_bfa_builds(self.group.bforartists_repo.download)


class ShortcutsPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizards.shortcuts.title"))
        self.setSubTitle(t("wizards.shortcuts.subtitle"))

        self.platform = get_platform()
        self.layout_ = QVBoxLayout(self)

        explanation = ""
        self.explanation_label = QLabel(self)

        explanation = t(f"wizard.file_association.{self.platform}")
        if self.platform == "Windows":  # Give a subtitle relating to the registry
            self.explanation_label.setToolTip(t("wizard.file_association.win_reg_key"))

        self.explanation_label.setText(explanation)
        self.explanation_label.setWordWrap(True)

        self.use_file_associations = QCheckBox(t("wizard.file_association.name"), parent=self)

        self.select: FolderSelector | None = None
        if self.platform == "Linux":
            self.select = FolderSelector(
                parent,
                default_folder=get_default_shortcut_folder(),
                check_relatives=False,
            )
            self.select.setEnabled(False)
            self.use_file_associations.toggled.connect(self.select.setEnabled)
            self.layout_.addWidget(self.select)
        elif self.platform == "Windows":
            self.addtostart = QCheckBox(t("wizard.shortcuts.start_menu"), parent=self)
            self.addtostart.setChecked(True)
            self.addtodesk = QCheckBox(t("wizard.shortcuts.desktop"), parent=self)
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
                    pth = self.select.path / get_default_program_shortcut_destination().name
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
                    get_default_program_shortcut_destination(),
                    exe=str(self.prop_settings.exe_location),
                )
            if self.addtodesk.isChecked():
                desktop = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, None, 0))

                try:
                    generate_program_shortcut(
                        desktop,
                        exe=str(self.prop_settings.exe_location),
                    )
                except Exception as e:
                    raise Exception(f"Exceptions raised while generating desktop shortcuts: {e}") from e


class AppearancePage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizard.appearance.title"))
        self.setSubTitle(t("wizard.appearance.subtitle"))
        self.layout_ = QVBoxLayout(self)

        self.titlebar = QCheckBox(t("wizard.appearance.titlebar"), self)
        self.titlebar.setChecked(get_use_system_titlebar())
        if get_platform() == "Linux":
            titlebar_label = QLabel(t("wizard.appearance.titlebar_label"), self)
        else:
            titlebar_label = QLabel(t("wizard.appearance.titlebar_label_linux"), self)
        self.dpi_scale_factor = QDoubleSpinBox(self)
        self.dpi_scale_factor.setRange(0.25, 10.0)
        self.dpi_scale_factor.setSingleStep(0.25)
        self.dpi_scale_factor.setValue(get_dpi_scale_factor())
        if DPI_OVERRIDDEN:
            label = "settings.appearance.dpi_scale_factor_overridden"
            self.dpi_scale_factor.setEnabled(False)
        else:
            label = "settings.appearance.dpi_scale_factor"
        self.dpi_scale_label = QLabel(t(label))
        dpi_scale_desc = QLabel(t("wizard.appearance.dpi_scaling"), self)

        self.layout_.addWidget(titlebar_label)
        self.layout_.addWidget(self.titlebar)
        self.layout_.addWidget(dpi_scale_desc)
        self.layout_.addWidget(self.dpi_scale_label)
        self.layout_.addWidget(self.dpi_scale_factor)

    def evaluate(self):
        set_use_system_titlebar(self.titlebar.isChecked())
        set_dpi_scale_factor(self.dpi_scale_factor.value())


class BackgroundRunningPage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizard.background.title"))
        self.setSubTitle(t("wizard.background.subtitle"))
        self.layout_ = QVBoxLayout(self)

        self.enable_btn = QCheckBox(t("wizard.background.show_tray_icon"))
        self.enable_btn.setChecked(get_show_tray_icon())
        self.layout_.addWidget(self.enable_btn)

    def evaluate(self):
        set_show_tray_icon(self.enable_btn.isChecked())


class CommittingPage(QWizardPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle(t("wizard.committing.title"))
        self.setSubTitle(t("wizard.committing.subtitle"))


class ErrorOccurredPage(QWizardPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle(t("wizard.error.title"))
        self.layout_ = QVBoxLayout(self)
        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.layout_.addWidget(self.output)
        self.layout_.addWidget(QLabel(t("wizard.error.continue"), self))
