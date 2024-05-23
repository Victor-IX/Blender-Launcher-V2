from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton


class LeftIconButtonWidget(QPushButton):
    def __init__(self, text, icon=None, parent=None):
        super().__init__(parent)
        self.setText(" ")

        if icon is not None:
            self.setIcon(icon)

        self.setStyleSheet("text-align:left; padding-left: 4px;")
        self.setLayout(QHBoxLayout())

        self.label = QLabel(text)
        self.label.setStyleSheet("padding-left: -4px;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.layout().addWidget(self.label)

    def set_text(self, text):
        self.label.setText(text)
