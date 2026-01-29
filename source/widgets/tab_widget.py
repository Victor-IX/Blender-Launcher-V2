from PySide6.QtWidgets import QHBoxLayout, QWidget


class TabWidget(QWidget):
    def __init__(self, parent, label="New Tab"):
        super().__init__(parent)

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(self._layout)
        parent.addTab(self, label)

    def _add_widget(self, widget):
        self._layout.addWidget(widget)
