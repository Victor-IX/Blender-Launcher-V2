from i18n import t
from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from .settings_group import SettingsGroup


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

        self.form: QFormLayout = QFormLayout(self)
        self.form.setContentsMargins(6, 0, 6, 0)
        self.form.setSpacing(6)
        self.label_width = label_width

    def addRow(self, *args, **kwargs):
        self.form.addRow(*args, **kwargs)

    def _addRow(self, label_text, widget, new_line=False, height=24):
        label = QLabel(label_text)
        label.setFixedWidth(self.label_width)
        label.setFixedHeight(height)

        if new_line:
            self.form.addRow(label)
            self.form.addRow(widget)
        else:
            self.form.addRow(label, widget)

        return SettingsFormWidgetRow(label, widget)

    def group(self, label: str) -> SettingsGroup:
        grp = SettingsGroup(t(label), parent=self)
        self.addRow(grp)
        return grp
