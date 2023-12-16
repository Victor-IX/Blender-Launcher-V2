from PyQt5.QtWidgets import QFileDialog


class FileDialogWindow(QFileDialog):
    def __init__(self):
        super().__init__()

    def getExistingDirectory(self, parent, title, directory):
        options = (
            QFileDialog.DontUseNativeDialog |
            QFileDialog.ShowDirsOnly |
            QFileDialog.HideNameFilterDetails |
            QFileDialog.DontUseCustomDirectoryIcons)
        return super().getExistingDirectory(
            parent, title, directory, options)
