from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from enum import Enum
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from typing import List, Tuple, Optional
from windows.base_window import BaseWindow


class DialogIcon(Enum):
    WARNING = 1
    INFO = 2


class PopupWidget(BaseWindow):
    accepted = pyqtSignal()
    cancelled = pyqtSignal()
    custom_signal = pyqtSignal(str)

    def __init__(
        self,
        title: str,
        message: str,
        info_popup: Optional[bool] = False,
        icon=DialogIcon.INFO,
        buttons: Optional[List[Tuple[str, str]]] = None,
        parent=None,
        app=None,
    ):
        """
        Popup class.

        :param title:   The title of the popup.
        :param message: The message to display in the popup.
        :param buttons: Optional. A list of tuples with the button label and the button role.
                        If not provided, the popup will have an OK and a Cancel button.
        :param info_popup: Optional. If True, the popup will be an information popup with only a Ok button.
        :param parent: The parent widget. Optional.
        """
        super().__init__(parent=parent, app=app)

        self.title = title
        self.message = message
        self.info_popup = info_popup
        self.buttons = buttons

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(self.title)
        self.setFixedSize(200, 70)

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
        self.PopupLayout.addWidget(message_label)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._add_buttons()

        self.show()

    def _add_buttons(self):
        if self.buttons:
            for label, role in self.buttons:
                button = QPushButton(label)
                button.setProperty("Popup", True)
                button.clicked.connect(lambda _, r=role: self.done(r))
                self.PopupLayout.addWidget(button)
        elif self.info_popup:
            ok_button = QPushButton("Ok")
            ok_button.setProperty("Popup", True)
            ok_button.clicked.connect(self.accept)
            self.PopupLayout.addWidget(ok_button)
        else:
            ok_button = QPushButton("Ok")
            ok_button.setProperty("Popup", True)
            ok_button.clicked.connect(self.accept)
            cancel_button = QPushButton("Cancel")
            cancel_button.setProperty("Popup", True)
            cancel_button.clicked.connect(self.cancel)

            button_layout = QHBoxLayout()
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            self.PopupLayout.addLayout(button_layout)

    def _custom_signal(self, role):
        self.custom_signal.emit(role)
        self.close()

    def accept(self):
        self.accepted.emit()
        self.close()

    def cancel(self):
        self.cancelled.emit()
        self.close()
