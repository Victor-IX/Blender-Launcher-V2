from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QLabel


class ElidedTextLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text: str = text
        self.metrics = QFontMetrics(self.font())

    def set_text(self, text):
        self.text = text

    def setElidedText(self):
        width = self.width()
        elided_text = self.metrics.elidedText(self.text, Qt.TextElideMode.ElideRight, width)
        self.setText(elided_text)

    def resizeEvent(self, event):
        self.setElidedText()
