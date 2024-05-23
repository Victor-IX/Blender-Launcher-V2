from PyQt5.QtWidgets import QFormLayout, QLabel, QWidget


class SettingsFormWidgetRow:
    def __init__(self, label, widget):
        super().__init__()
        self.label = label
        self.widget = widget

    def setEnabled(self, enabled=True):
        self.label.setEnabled(enabled)
        self.widget.setEnabled(enabled)


class SettingsFormWidget(QWidget):
    def __init__(self, label_width=240, parent=None):
        super().__init__(parent)

        self.layout: QFormLayout = QFormLayout(self)
        self.layout.setContentsMargins(6, 0, 6, 0)
        self.layout.setSpacing(6)
        self.label_width = label_width

    def addRow(self, *args, **kwargs):
        self.layout.addRow(*args, **kwargs)

    def _addRow(self, label_text, widget, new_line=False, height=24):
        label = QLabel(label_text)
        label.setFixedWidth(self.label_width)
        label.setFixedHeight(height)

        if new_line:
            self.layout.addRow(label)
            self.layout.addRow(widget)
        else:
            self.layout.addRow(label, widget)

        return SettingsFormWidgetRow(label, widget)
