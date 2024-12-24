from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QWidget


class FileDialogWindow(QFileDialog):
    def __init__(self):
        super().__init__()

    def get_directory(self, parent, title, directory):
        options = (
            QFileDialog.DontUseNativeDialog
            | QFileDialog.ShowDirsOnly
            | QFileDialog.HideNameFilterDetails
            | QFileDialog.DontUseCustomDirectoryIcons
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
            caption=title,
            directory=directory,
            options=(
                QFileDialog.DontUseNativeDialog
                | QFileDialog.HideNameFilterDetails
                | QFileDialog.DontUseCustomDirectoryIcons
            ),
        )

    def get_save_filename(
        self,
        parent: QWidget | None = None,
        title: str | None = None,
        directory: str | None = None,
    ):
        return QFileDialog.getSaveFileName(
            parent=parent,
            caption=title,
            directory=directory,
            options=(
                QFileDialog.DontUseNativeDialog
                | QFileDialog.HideNameFilterDetails
                | QFileDialog.DontUseCustomDirectoryIcons
            ),
        )
