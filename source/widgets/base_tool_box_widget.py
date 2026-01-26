from typing import Unpack

from modules.version_matcher import VersionSearchQuery, VSQKwargs
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QTabBar


class BaseToolBoxWidget(QTabBar):
    tab_changed = Signal(int)
    query_changed = Signal(VersionSearchQuery)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ = parent
        self.tab_to_query: dict[int, VersionSearchQuery] = {}

        self.setContentsMargins(0, 0, 0, 0)
        self.setShape(QTabBar.Shape.RoundedWest)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Minimum)
        self.setExpanding(False)
        self.setProperty("West", True)
        self.setDrawBase(False)
        self.currentChanged.connect(self.current_changed)

    def add_tab(self, name: str, **restrictions: Unpack[VSQKwargs]):
        self.addTab(name)
        index = self.count() - 1
        self.tab_to_query[index] = VersionSearchQuery(**restrictions)

    def current_changed(self, i):
        self.tab_changed.emit(i)
        query = self.tab_to_query.get(i, ())
        if query:
            self.query_changed.emit(query)

    def current_query(self) -> VersionSearchQuery:
        return self.tab_to_query.get(self.currentIndex(), VersionSearchQuery.any())

    def update_visibility(self, idx: int, b: bool):
        self.setTabVisible(idx, b)
        self.setTabEnabled(idx, b)
        self.hide()
        self.show()
