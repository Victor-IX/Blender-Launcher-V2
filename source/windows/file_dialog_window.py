from __future__ import annotations

from modules.container_detect import IS_CONTAINED
from PySide6.QtWidgets import QFileDialog, QWidget

Option = QFileDialog.Option


DIALOG_OPTIONS = Option.HideNameFilterDetails
if not IS_CONTAINED:
    DIALOG_OPTIONS |= Option.DontUseNativeDialog | Option.DontUseCustomDirectoryIcons


class FileDialogWindow(QFileDialog):
    def __init__(self):
        super().__init__()

    def get_directory(self, parent, title, directory):
        options = DIALOG_OPTIONS | Option.ShowDirsOnly
        return QFileDialog.getExistingDirectory(parent, title, directory, options)

    def get_open_filename(
        self,
        parent: QWidget | None = None,
        title: str | None = None,
        directory: str | None = None,
    ):
        return QFileDialog.getOpenFileName(
            parent=parent,
            caption=title or "",
            dir=directory or "",
            options=DIALOG_OPTIONS,
        )

    def get_save_filename(
        self,
        parent: QWidget | None = None,
        title: str | None = None,
        directory: str | None = None,
    ):
        return QFileDialog.getSaveFileName(
            parent=parent,
            caption=title or "",
            dir=directory or "",
            options=DIALOG_OPTIONS,
        )
