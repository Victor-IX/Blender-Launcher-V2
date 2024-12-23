from enum import Enum
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QKeyEvent
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget

from windows.base_window import BaseWindow


class DialogIcon(Enum):
    WARNING = 1
    INFO = 2


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
            button_layout = QHBoxLayout()

            for label in self.buttons:
                button = QPushButton(label)
                button.setProperty("Popup", True)
                button.clicked.connect(lambda _, lbl=label: self._custom_signal(lbl))
                button_layout.addWidget(button)

            self.PopupLayout.addLayout(button_layout)

        elif self.info_popup:
            ok_button = QPushButton("Ok")
            ok_button.setProperty("Popup", True)
            ok_button.clicked.connect(self._accept)
            self.PopupLayout.addWidget(ok_button)
        else:
            ok_button = QPushButton("Ok")
            ok_button.setProperty("Popup", True)
            ok_button.clicked.connect(self._accept)
            cancel_button = QPushButton("Cancel")
            cancel_button.setProperty("Popup", True)
            cancel_button.clicked.connect(self._cancel)

            button_layout = QHBoxLayout()
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            self.PopupLayout.addLayout(button_layout)

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
