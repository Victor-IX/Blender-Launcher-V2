from __future__ import annotations

import textwrap
from enum import Enum

from i18n import t
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from windows.base_window import BaseWindow


class PopupIcon(Enum):
    WARNING = 1
    INFO = 2
    NONE = 3


class PopupButton(Enum):
    OK = "msg.tool.ok"
    ACCEPT = "msg.tool.accept"
    CANCEL = "msg.tool.cancel"
    QUIT = "msg.tool.quit"
    NEXT = "msg.tool.next"
    PREV = "msg.tool.prev"
    CONT = "msg.tool.cont"
    FINISH = "msg.tool.finish"
    YES = "msg.tool.yes"
    NO = "msg.tool.no"
    RETRY = "msg.tool.retry"
    UPDATE = "msg.tool.update"
    LATER = "msg.tool.later"

    RESTART_NOW = "msg.tool.restart_now"
    TRASH = "msg.tool.trash"
    REMOVE = "msg.tool.remove"
    DELETE = "msg.tool.delete"
    DONT_SHOW_AGAIN = "msg.tool.dont_show_again"
    MIGRATE = "msg.tool.migrate"
    OVERWRITE = "msg.tool.overwrite"
    GENERAL_FOLDER = "msg.tool.general_folder"
    KEEP_BOTH_VERSIONS = "msg.tool.keep_both_versions"
    MOVE_TO_NEW = "msg.tool.move_to_new"
    REMOVE_SETTINGS = "msg.tool.remove_settings"

    @staticmethod
    def info() -> list[PopupButton]:
        return [PopupButton.OK]

    @staticmethod
    def default() -> list[PopupButton]:
        return [PopupButton.OK, PopupButton.CANCEL]

    @staticmethod
    def yn() -> list[PopupButton]:
        return [PopupButton.YES, PopupButton.NO]


class PopupWindow(BaseWindow):
    accepted = Signal()
    cancelled = Signal()
    custom_signal = Signal(PopupButton)

    def __init__(
        self,
        message: str,
        title: str = "Info",
        icon=PopupIcon.INFO,
        buttons: PopupButton | list[PopupButton] | None = None,
        parent=None,
        app=None,
    ):
        """
        Popup class.

        :param title:   The title of the popup (only visible when system title bar is enabled).
        :param message: The message to display in the popup.
        :param buttons: Optional. A list of tuples with the button label and the button role.
                        If not provided, the popup will have an OK and a Cancel button.
        :param info_popup: Optional. If True, the popup will be an information popup with only an OK button.
        :param icon: Optional. The icon to display in the popup. Can be `PopupIcon.INFO` for an info icon
                     or `PopupIcon.WARNING` for a warning icon. Defaults to `PopupIcon.INFO`.
        :param parent: The parent widget. Optional.
        """
        super().__init__(parent=parent, app=app)

        self.title = title
        self.message = message

        if buttons is None:
            buttons = PopupButton.default()
        elif isinstance(buttons, PopupButton):
            buttons = [buttons]

        self.btns: list[PopupButton] = buttons

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(self.title)
        self.setMinimumSize(200, 100)

        self.PopupWidget = QWidget(self)
        self.PopupLayout = QVBoxLayout(self.PopupWidget)
        self.PopupLayout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(self.PopupWidget)

        self.IconLabel = QLabel()
        self.IconLabel.setScaledContents(True)
        self.IconLabel.setFixedSize(24, 24)

        if icon == PopupIcon.WARNING:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/exclamation.svg"))
        elif icon == PopupIcon.INFO:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/info.svg"))
        else:
            self.IconLabel.hide()

        # Wrap the message text manually, using message_label.setWordWrap(True) don't work as expected for some reason
        wrapped_lines = []
        for line in message.splitlines():
            if not line.strip():
                wrapped_lines.append("")
            else:
                wrapped = textwrap.wrap(line, width=70)
                wrapped_lines.extend(wrapped)
        wrapped_message = "\n".join(wrapped_lines)

        message_label = QLabel(wrapped_message)

        self.TextLayout = QHBoxLayout()
        self.TextLayout.setContentsMargins(4, 4, 6, 0)
        self.TextLayout.addWidget(self.IconLabel)
        self.TextLayout.addSpacing(5)
        self.TextLayout.addWidget(message_label)

        self.PopupLayout.addLayout(self.TextLayout)

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowMinimizeButtonHint & ~Qt.WindowType.WindowMaximizeButtonHint
        )
        self._add_buttons()
        self.show()
        self.setFixedSize(self.size())

    def _add_buttons(self):
        button_layout = QHBoxLayout()

        if len(self.btns) > 2:
            for key in self.btns:
                button = self._create_button(key, self._custom_signal)
                button_layout.addWidget(button)
        elif len(self.btns) == 2:
            ok_button = self._create_button(self.btns[0], self._accept)
            cancel_button = self._create_button(self.btns[1], self._cancel)
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
        else:
            ok_button = self._create_button(self.btns[0], self._accept)
            button_layout.addWidget(ok_button)

        self.PopupLayout.addLayout(button_layout)

    def _create_button(self, btn: PopupButton, callback):
        button = QPushButton(t(btn.value))
        button.setProperty("Popup", True)
        button.clicked.connect(lambda _, lbl=btn: callback(lbl) if callback == self._custom_signal else callback())
        return button

    def _custom_signal(self, label: PopupButton):
        self.custom_signal.emit(label)
        self.close()

    def _accept(self):
        self.accepted.emit()
        self.close()

    def _cancel(self):
        self.cancelled.emit()
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape and self.btns != PopupButton.info():
            self._cancel()
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._accept()
