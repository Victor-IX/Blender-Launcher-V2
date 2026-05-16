from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import QMenu


class BaseMenuWidget(QMenu):
    holding_shift = Signal(bool)

    def __init__(self, title="", parent=None):
        super().__init__(title=title, parent=parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.NoDropShadowWindowHint)
        self.setToolTipsVisible(True)

    def trigger(self):
        actions = self.actions()
        actions_count = sum((a.isVisible() and not a.isSeparator()) for a in actions)

        if actions_count == 0:
            return

        self.exec_(QCursor.pos())

    def enable_shifting(self):
        """This is an optional feature because it can be very expensive to do this all the time."""
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if isinstance(event, QKeyEvent):
            self.holding_shift.emit(
                event.modifiers() in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier)
            )

        return super().eventFilter(obj, event)
