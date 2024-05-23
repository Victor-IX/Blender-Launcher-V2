from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLineEdit


class BaseLineEdit(QLineEdit):
    returnPressed = pyqtSignal()
    escapePressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Return:
            self.returnPressed.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)

        if event.reason() == Qt.FocusReason.MouseFocusReason:
            self.escapePressed.emit()
