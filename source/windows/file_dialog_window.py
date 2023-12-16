from PyQt5.QtWidgets import QFileDialog


class FileDialogWindow(QFileDialog):
    def __init__(self):
        super().__init__()

    def get_directory(self, parent, title, directory):
        options = (
            QFileDialog.DontUseNativeDialog |
            QFileDialog.ShowDirsOnly |
            QFileDialog.HideNameFilterDetails |
            QFileDialog.DontUseCustomDirectoryIcons)
        return QFileDialog.getExistingDirectory(
            parent, title, directory, options)
