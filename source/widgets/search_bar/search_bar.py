from __future__ import annotations

from i18n import t
from modules.version_matcher import VersionSearchQuery
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QWidget,
)


class SearchBarWidget(QFrame):
    query = Signal(VersionSearchQuery)

    def __init__(self, parent=None):
        super().__init__(parent)

        # self.setMinimumHeight(100)
        self.setProperty("SettingsGroup", True)
        # self.setFrameShape(QFrame.Shape.Panel)

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)

        self.grid.addWidget(QLabel("Hiiii", self), 1, 0, 1, 1)

        self.fuzzy_text = QLineEdit(self)
        self.fuzzy_text.setPlaceholderText("Search . . .")
        self.fuzzy_text.returnPressed.connect(self.query_updated)
        self.grid.addWidget(self.fuzzy_text, 0, 0, 1, 2)

    def query_updated(self):
        self._q = self._generate_query()
        self.query.emit(self._q)

    def _generate_query(self) -> VersionSearchQuery:
        return VersionSearchQuery(
            fuzzy_text=self.fuzzy_text.text() or None,
        )
