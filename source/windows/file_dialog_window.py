from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QWidget

Option = QFileDialog.Option


class FileDialogWindow(QFileDialog):
    def __init__(self):
        super().__init__()

    def get_directory(self, parent, title, directory):
        options = (
            Option.DontUseNativeDialog
            | Option.ShowDirsOnly
            | Option.HideNameFilterDetails
            | Option.DontUseCustomDirectoryIcons
        )
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
            options=(Option.DontUseNativeDialog | Option.HideNameFilterDetails | Option.DontUseCustomDirectoryIcons),
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
            options=(Option.DontUseNativeDialog | Option.HideNameFilterDetails | Option.DontUseCustomDirectoryIcons),
        )
