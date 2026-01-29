from modules.build_info import BuildInfo
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QListWidgetItem


class EnablableListWidgetItem(QListWidgetItem):
    def __init__(self, enabled_font: QFont, disable_font: QFont, build: BuildInfo, parent=None):
        super().__init__(parent)
        self._enabled = True
        self.__enabled_font = enabled_font
        self.__disable_font = disable_font
        self.build = build

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if value:
            self.setFont(self.__enabled_font)
        else:
            self.setFont(self.__disable_font)

    def __lt__(self, other: QListWidgetItem):
        if not isinstance(other, EnablableListWidgetItem):
            return False
        return self.enabled < other.enabled if self.enabled != other.enabled else self.build < other.build
