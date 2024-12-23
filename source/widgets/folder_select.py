from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from modules._platform import get_cwd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)
from windows.popup_window import PopupWindow, DialogIcon
from windows.file_dialog_window import FileDialogWindow

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class FolderSelector(QWidget):
    validity_changed = Signal(bool)
    folder_changed = Signal(Path)

    def __init__(
        self,
        launcher: BlenderLauncher,
        *,
        default_folder: Path | None = None,
        default_choose_dir_folder: Path | None = None,
        check_relatives=True,
        check_perms=True,
        parent=None,
    ):
        super().__init__(parent)
        self.launcher = launcher
        self.line_edit = QLineEdit()
        self.default_folder = default_folder
        self.default_choose_dir = default_choose_dir_folder or self.default_folder or Path(".")
        self.check_relatives = check_relatives
        self.check_perms = check_perms

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
        if not new_library_folder:
            return
        if self.check_relatives:
            self.set_folder(Path(new_library_folder))
        else:
            self.line_edit.setText(new_library_folder)
            self.default_choose_dir = new_library_folder
            if (self.check_perms and self.check_write_permission()) or not self.check_perms:
                self.folder_changed.emit(new_library_folder)

    def set_folder(self, folder: Path, relative: bool | None = None):
        if folder.is_relative_to(get_cwd()):
            if relative is None:
                self.dlg = PopupWindow(
                    parent=self.launcher,
                    title="Setup",
                    message="The selected path is relative to the executable's path.<br>\
                        Would you like to save it as relative?<br>\
                        This is useful if the folder may move.",
                    icon=DialogIcon.NONE,
                    buttons=["Yes", "No"],
                )
                self.dlg.accepted.connect(lambda: self.set_folder(folder, True))
                self.dlg.cancelled.connect(lambda: self.set_folder(folder, False))
                return

            if relative:
                folder = folder.relative_to(get_cwd())

        self.line_edit.setText(str(folder))
        self.default_choose_dir = folder
        if (self.check_perms and self.check_write_permission()) or not self.check_perms:
            self.folder_changed.emit(folder)

    def check_write_permission(self) -> bool:
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
            self.validity_changed.emit(can_write)

        return can_write

    @property
    def is_valid(self) -> bool:
        return self.__is_valid

    @property
    def path(self):
        if t := self.line_edit.text():
            return Path(t)
        return None
