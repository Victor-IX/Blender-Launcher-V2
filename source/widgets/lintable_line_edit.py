from PySide6.QtWidgets import QLineEdit


class LintableLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._valid = True

    def valid(self):
        return self._valid

    def set_valid(self, value: bool):
        self._valid = value
        self.setStyleSheet("border-color : %s" % ("red" if not self._valid else ""))
