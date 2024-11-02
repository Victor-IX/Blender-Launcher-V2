from __future__ import annotations

import contextlib
import sys
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from modules._platform import get_cwd, get_platform
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
from windows.dialog_window import DialogWindow
from windows.file_dialog_window import FileDialogWindow

if TYPE_CHECKING:
    from semver import Version
    from windows.main_window import BlenderLauncher


class BasicOnboardingPage(QWizardPage):
    @abstractmethod
    def evaluate(self):
        """Runs the settings and make sure everything is set up correctly before BLV2 init"""
        raise NotImplementedError


class WelcomePage(BasicOnboardingPage):
    def __init__(self, v: Version, parent=None):
        super().__init__(parent=parent)
        self.setTitle(f"Welcome to Blender Launcher v{v}!")
        self.layout_ = QHBoxLayout(self)

        self.label = QLabel(
            "In this First-Time Setup, we will walk through the most common settings you will likely want to configure.<br>\
                            you only have to do this once and never again."
        )
        self.label.setWordWrap(True)
        font = self.label.font()
        font.setPointSize(14)
        self.label.setFont(font)

        self.layout_.addWidget(self.label)

    def evaluate(self): ...


class FolderSelectGroup(QWidget):
    validity_changed = pyqtSignal()

    def __init__(
        self,
        launcher: BlenderLauncher,
        *,
        default_folder: Path | None = None,
        default_choose_dir_folder: Path | None = None,
        check_relatives=True,
        parent=None,
    ):
        super().__init__(parent)
        self.launcher = launcher
        self.line_edit = QLineEdit()
        self.default_folder = default_folder
        self.default_choose_dir = default_choose_dir_folder or self.default_folder or Path(".")
        self.check_relatives = check_relatives

        if default_folder is not None:
            self.line_edit.setText(str(default_folder))
        self.line_edit.setReadOnly(True)
        self.line_edit.textChanged.connect(self.check_write_permission)
        self.button = QPushButton(launcher.icons.folder, "")
        self.button.setFixedWidth(25)
        self.button.clicked.connect(self.prompt_folder)
        self.__is_valid = False
        self.check_write_permission()

        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        self.layout_.addWidget(self.line_edit)
        self.layout_.addWidget(self.button)

    def prompt_folder(self):
        new_library_folder = FileDialogWindow().get_directory(self, "Select Folder", str(self.default_choose_dir))
        if self.check_relatives:
            self.set_folder(Path(new_library_folder))
        else:
            self.line_edit.setText(new_library_folder)
            self.check_write_permission()

    def set_folder(self, folder: Path, relative: bool | None = None):
        if folder.is_relative_to(get_cwd()):
            if relative is None:
                self.dlg = DialogWindow(
                    parent=self.launcher,
                    title="Setup",
                    text="The selected path is relative to the executable's path.<br>\
                        Would you like to save it as relative?<br>\
                        This is useful if the folder may move.",
                    accept_text="Yes",
                    cancel_text="No",
                )
                self.dlg.accepted.connect(lambda: self.set_folder(folder, True))
                self.dlg.cancelled.connect(lambda: self.set_folder(folder, False))
                return

            if relative:
                folder = folder.relative_to(get_cwd())

        self.line_edit.setText(str(folder))
        self.check_write_permission()

    def check_write_permission(self):
        if not self.line_edit.text():
            return

        path = Path(self.line_edit.text())
        if not path.exists():
            for parent in path.parents:
                if parent.exists():
                    path = parent
                    break

        # check if the folder can be written to
        can_write = False
        with contextlib.suppress(OSError):
            tempfile = path / "tempfile_checking_write_perms"
            with tempfile.open("w") as f:
                f.write("check,check,check")
            tempfile.unlink()
            can_write = True

        # warn the user by changing the highlight color of the line edit
        old_valid = self.__is_valid
        self.__is_valid = can_write
        if can_write:
            self.line_edit.setStyleSheet("border-color:")
            self.line_edit.setToolTip("")
        else:
            self.line_edit.setStyleSheet("border-color: red")
            self.line_edit.setToolTip("The requested location has no write permissions!")
        if old_valid != can_write:
            self.validity_changed.emit()

    @property
    def is_valid(self) -> bool:
        return self.__is_valid

    @property
    def path(self):
        if t := self.line_edit.text():
            return Path(t)
        return None


class ChooseLibraryPage(BasicOnboardingPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle("First, choose where Blender builds will be stored")
        self.setSubTitle(
            "Make sure that this folder has enough storage to download and store all the builds you want. This can be changed in the future."
        )

        self.lf = FolderSelectGroup(
            parent,
            default_folder=get_actual_library_folder_no_fallback() or None,
            default_choose_dir_folder=get_actual_library_folder(),
            parent=self,
        )
        self.layout_ = QVBoxLayout(self)
        self.layout_.addWidget(QLabel("Library location: ", self))
        self.layout_.addWidget(self.lf)

        self.lf.validity_changed.connect(self.completeChanged)

    def isComplete(self) -> bool:
        return self.lf.is_valid

    def evaluate(self):
        set_library_folder(str(Path(self.lf.line_edit.text())))


class RepoItem(QGroupBox):
    def __init__(
        self,
        name: str,
        description: str,
        default_library: bool = True,
        library: bool = True,
        default_download: bool = True,
        download: bool = True,
        parent: BlenderLauncher | None = None,
    ):
        super().__init__(parent)
        self.name = name

        self.title_label = QLabel(name, self)
        font = QFont(self.title_label.font())
        font.setPointSize(12)
        font.setBold(True)
        self.title_label.setFont(font)
        self.description = QLabel(description, self)
        self.description.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.library_enable_button = QCheckBox(self)
        self.library_enable_button.setProperty("Visibility", True)
        self.library_enable_button.setChecked(default_library)
        self.library_enable_button.setText(None)
        if not library:
            self.library_enable_button.setEnabled(False)

        self.download_enable_button = QCheckBox(self)
        self.download_enable_button.setProperty("Download", True)
        self.download_enable_button.setChecked(default_download)
        self.download_enable_button.setText(None)

        if not download:
            self.download_enable_button.setEnabled(False)

        self.layout_ = QGridLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        self.layout_.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.layout_.addWidget(self.title_label, 0, 0, 1, 1)
        self.layout_.addWidget(self.description, 1, 0, 1, 1)
        self.layout_.addWidget(self.library_enable_button, 0, 1, 2, 1)
        self.layout_.addWidget(self.download_enable_button, 0, 2, 2, 1)

    def add_library_to_group(self, grp: QButtonGroup):
        grp.addButton(self.library_enable_button)
        grp.buttonToggled.connect(self.library_toggled)

    def add_downloads_to_group(self, grp: QButtonGroup):
        grp.addButton(self.download_enable_button)
        grp.buttonToggled.connect(self.download_toggled)

    def library_toggled(self, btn: QCheckBox, checked: bool):
        if btn is not self and checked != self.library_enable_button.isChecked():
            self.library_enable_button.setChecked(checked)

    def download_toggled(self, btn: QCheckBox, checked: bool):
        if btn is not self and checked != self.download_enable_button.isChecked():
            self.download_enable_button.setChecked(checked)

    @property
    def download(self):
        return self.download_enable_button.isChecked()

    @property
    def library(self):
        return self.library_enable_button.isChecked()


class RepoSelectPage(BasicOnboardingPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle("Choose which repositories you want enabled")
        self.setSubTitle(
            "This will enable/disable certain builds of blender to be visible / scraped. This can be changed in the future."
        )
        self.layout_ = QVBoxLayout(self)

        self.item_list = QListWidget(self)
        self.item_list.setAlternatingRowColors(True)
        self.layout_.addWidget(self.item_list)

        self.stable_repo = RepoItem(
            "stable",
            "The builds that come from the stable build",
            default_library=True,
            default_download=get_scrape_stable_builds(),
            parent=parent,
        )
        self.daily_repo = RepoItem(
            "daily",
            "Builds created every day. They the latest features and bug fixes, but they can be unstable",
            default_library=True,
            default_download=get_scrape_automated_builds(),
            parent=parent,
        )
        self.experimental_repo = RepoItem(
            "experimental",
            "These have new features that may end up in official Blender releases. They can be unstable.",
            default_library=True,
            default_download=get_scrape_automated_builds(),
            parent=parent,
        )
        self.patch_repo = RepoItem(
            "patch",
            "Patch based builds",
            default_library=True,
            default_download=get_scrape_automated_builds(),
            parent=parent,
        )
        self.bforartists_repo = RepoItem(
            "bforartists",
            "A popular fork of Blender with the goal of improving the UI.",
            default_library=True,
            default_download=get_scrape_stable_builds(),
            parent=parent,
        )

        self.exp_and_patch_groups = QButtonGroup()
        self.exp_and_patch_groups.setExclusive(False)
        self.experimental_repo.add_library_to_group(self.exp_and_patch_groups)
        self.patch_repo.add_library_to_group(self.exp_and_patch_groups)

        self.automated_groups = QButtonGroup()
        self.automated_groups.setExclusive(False)
        self.daily_repo.add_downloads_to_group(self.automated_groups)
        self.experimental_repo.add_downloads_to_group(self.automated_groups)
        self.patch_repo.add_downloads_to_group(self.automated_groups)

        item_list_items = [
            self.stable_repo,
            self.daily_repo,
            self.experimental_repo,
            self.patch_repo,
            self.bforartists_repo,
        ]

        for widget in item_list_items:
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)  # type: ignore
            self.item_list.addItem(item)
            self.item_list.setItemWidget(item, widget)

    def evaluate(self):
        set_scrape_stable_builds(self.stable_repo.download)
        set_scrape_automated_builds(self.daily_repo.download)
        set_scrape_bfa_builds(self.bforartists_repo.download)

        # TODO implement the visibility options


class FileAssociationPage(BasicOnboardingPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle("Launching Blendfiles (.blend, .blend1) from BLV2 directly")
        subtitle = 'This will allow you to automatically launch the correct version for a file\
 using the "Open With.." functionality on your desktop environment. This process is fully reversible.'
        self.setSubTitle(subtitle)

        self.layout_ = QVBoxLayout(self)
        explanation = ""
        platform = get_platform()
        self.explanation_label = QLabel(self)
        if platform == "Windows":  # Give a subtitle relating to the registry
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
        if platform == "Linux":
            explanation = """In order to do this on Linux, we will generate a .desktop file at the requested location.\
 It contains mimetype data which tells the environment what files the program expects to handle.

The default location is typically searched by desktop environments for user program entries.
"""
        self.explanation_label.setText(explanation)
        self.explanation_label.setWordWrap(True)
        self.layout_.addWidget(self.explanation_label)

        self.use_file_associations = QCheckBox("Register for file associations", parent=self)
        self.layout_.addWidget(self.use_file_associations)

        self.select: FolderSelectGroup | None = None
        if platform == "Linux":
            self.select = FolderSelectGroup(
                parent,
                default_folder=get_default_shortcut_destination().parent,
                check_relatives=False,
            )
            self.layout_.addWidget(self.select)

    def evaluate(self):
        if not self.use_file_associations.isChecked():
            return

        if self.select is not None:  # then we should make a desktop file
            assert self.select.path is not None

            if self.select.path.is_dir():
                pth = self.select.path / get_default_shortcut_destination().name
            else:
                pth = self.select.path

            generate_program_shortcut(pth)
            return

        if sys.platform == "win32":
            register_windows_filetypes()


class AppearancePage(BasicOnboardingPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
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
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.setTitle("Running BLV2 in the background")
        self.setSubTitle("""BLV2 can be kept alive in the background with a system tray icon.\
 This can be useful for reading efficiency and other features, but it is not totally necessary.""")
        self.layout_ = QVBoxLayout(self)

        self.enable_btn = QCheckBox("Run BLV2 in the background (Minimise to tray)")
        self.enable_btn.setChecked(get_show_tray_icon())
        self.layout_.addWidget(self.enable_btn)

    def evaluate(self):
        set_show_tray_icon(self.enable_btn.isChecked())


class ErrorOccurredPage(QWizardPage):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        # self.setTitle("An Error occured")
        self.layout_ = QVBoxLayout(self)
        label = QLabel("An error occured during setup!", self)
        f = label.font()
        f.setPointSize(20)
        label.setFont(f)

        self.layout_.addWidget(label)
        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.layout_.addWidget(self.output)
        self.layout_.addWidget(QLabel("Continue anyways?", self))
