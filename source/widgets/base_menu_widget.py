from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import QApplication, QMenu


class BaseMenuWidget(QMenu):
    action_height = 30
    holding_shift = Signal(bool)

    def __init__(self, title="", parent=None):
        super().__init__(title=title, parent=parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.NoDropShadowWindowHint)
        self.action_height = BaseMenuWidget.action_height
        self.screen_size = QApplication.primaryScreen().geometry()
        self.setToolTipsVisible(True)

    def trigger(self):
        actions = self.actions()
        actions_count = sum((a.isVisible() and not a.isSeparator()) for a in actions)

        if actions_count == 0:
            return

        menu_height = actions_count * self.action_height
        reverse = False

        cursor = QCursor.pos()
        cursor.setX(int(cursor.x() - self.action_height * 0.5))

        if cursor.y() > (self.screen_size.height() - menu_height):
            reverse = True

        if reverse:
            actions.reverse()
            cursor.setY(int(cursor.y() - actions_count * self.action_height + 15))
        else:
            cursor.setY(int(cursor.y() - self.action_height * 0.5))

        i = 0

        for action in actions:
            if action.isVisible() and not action.isSeparator():
                if action.isEnabled():
                    self.setActiveAction(action)
                    cursor.setY(cursor.y() + i * (self.action_height if reverse else (-self.action_height)))
                    break

                i = i + 1

        self.exec_(cursor)

    def enable_shifting(self):
        """This is an optional feature because it can be very expensive to do this all the time."""
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if isinstance(event, QKeyEvent):
            self.holding_shift.emit(
                event.modifiers() in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier)
            )

        return super().eventFilter(obj, event)
