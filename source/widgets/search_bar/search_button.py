from enum import Enum

from modules.icons import Icons
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton

__all__ = ["SearchButtonWidget"]


class State(Enum):
    CLOSED = 0
    OPEN = 1


class SearchButtonWidget(QPushButton):
    State = State

    state_updated = Signal(State)

    def __init__(self, icons: Icons, parent=None):
        super().__init__(parent)
        self.setText("")

        self._icons = icons

        self._state: State = State.CLOSED
        self.setIcon(icons.search)

        self.clicked.connect(self.toggle_state)

    def toggle_state(self):
        if self._state == State.CLOSED:
            self._state = State.OPEN
            self.setIcon(self._icons.close)
        else:
            self._state = State.CLOSED
            self.setIcon(self._icons.search)
        self.state_updated.emit(self._state)
