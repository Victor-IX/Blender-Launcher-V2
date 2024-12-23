from enum import Enum
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QKeyEvent
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget

from windows.base_window import BaseWindow


class DialogIcon(Enum):
    WARNING = 1
    INFO = 2
    NONE = 3


class PopupWindow(BaseWindow):
    accepted = pyqtSignal()
    cancelled = pyqtSignal()
    custom_signal = pyqtSignal(str)

    def __init__(
        self,
        message: str,
        title: Optional[str] = "Info",
        info_popup: Optional[bool] = False,
        icon=DialogIcon.INFO,
        buttons: Optional[List[str]] = None,
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
        :param icon: Optional. The icon to display in the popup. Can be `DialogIcon.INFO` for an info icon
                     or `DialogIcon.WARNING` for a warning icon. Defaults to `DialogIcon.INFO`.
        :param parent: The parent widget. Optional.
        """
        super().__init__(parent=parent, app=app)

        self.title = title
        self.message = message
        self.info_popup = info_popup
        self.buttons = buttons

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(self.title)
        self.setFixedSize(200, 100)

        self.PopupWidget = QWidget(self)
        self.PopupLayout = QVBoxLayout(self.PopupWidget)
        self.PopupLayout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(self.PopupWidget)

        self.IconLabel = QLabel()
        self.IconLabel.setScaledContents(True)
        self.IconLabel.setFixedSize(24, 24)

        if icon == DialogIcon.WARNING:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/exclamation.svg"))
        elif icon == DialogIcon.INFO:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/info.svg"))
        else:
            self.IconLabel.hide()

        message_label = QLabel(message)
        message_label.setWordWrap(True)

        self.TextLayout = QHBoxLayout()
        self.TextLayout.setContentsMargins(4, 4, 6, 0)
        self.TextLayout.addWidget(self.IconLabel)
        self.TextLayout.addSpacing(5)
        self.TextLayout.addWidget(message_label)

        self.PopupLayout.addLayout(self.TextLayout)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinimizeButtonHint & ~Qt.WindowMaximizeButtonHint)
        self._add_buttons()
        self.show()

    def _add_buttons(self):
        if self.buttons:
            self._add_custom_buttons()
        elif self.info_popup:
            self._add_info_button()
        else:
            self._add_default_buttons()

    def _add_custom_buttons(self):
        button_layout = QHBoxLayout()

        if len(self.buttons) > 2:
            for label in self.buttons:
                button = self._create_button(label, self._custom_signal)
                button_layout.addWidget(button)
        elif len(self.buttons) == 2:
            ok_button = self._create_button(self.buttons[0], self._accept)
            cancel_button = self._create_button(self.buttons[1], self._cancel)
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
        else:
            ok_button = self._create_button(self.buttons[0], self._accept)
            button_layout.addWidget(ok_button)

        self.PopupLayout.addLayout(button_layout)

    def _add_info_button(self):
        ok_button = self._create_button("Ok", self._accept)
        self.PopupLayout.addWidget(ok_button)

    def _add_default_buttons(self):
        ok_button = self._create_button("Ok", self._accept)
        cancel_button = self._create_button("Cancel", self._cancel)

        button_layout = QHBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        self.PopupLayout.addLayout(button_layout)

    def _create_button(self, label, callback):
        button = QPushButton(label)
        button.setProperty("Popup", True)
        button.clicked.connect(lambda _, lbl=label: callback(lbl) if callback == self._custom_signal else callback())
        return button

    def _custom_signal(self, label: str):
        self.custom_signal.emit(label)
        self.close()

    def _accept(self):
        self.accepted.emit()
        self.close()

    def _cancel(self):
        self.cancelled.emit()
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape and not self.CancelButton.isHidden():
            self.cancel()
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.accept()
