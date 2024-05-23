from __future__ import annotations

from enum import Enum

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from windows.base_window import BaseWindow


class DialogIcon(Enum):
    WARNING = 1
    INFO = 2


class DialogWindow(BaseWindow):
    accepted = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(
        self,
        title="Warning",
        text="Dialog Window",
        accept_text="Accept",
        cancel_text: str | None = "Cancel",
        icon=DialogIcon.WARNING,
        parent=None,
        app=None,
    ):
        super().__init__(parent=parent, app=app)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(160, 60)

        sizePolicy = QSizePolicy(
            QSizePolicy.MinimumExpanding,
            QSizePolicy.MinimumExpanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        self.CentralWidget = QWidget(self)
        self.CentralLayout = QVBoxLayout(self.CentralWidget)
        self.CentralLayout.setContentsMargins(6, 6, 6, 6)
        self.CentralLayout.setSpacing(0)
        self.setCentralWidget(self.CentralWidget)
        self.setWindowTitle(title)

        self.IconLabel = QLabel()
        self.IconLabel.setScaledContents(True)
        self.IconLabel.setFixedSize(48, 48)

        if icon == DialogIcon.WARNING:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/exclamation.svg"))
        elif icon == DialogIcon.INFO:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/info.svg"))

        self.TextLabel = QLabel(text)
        self.TextLabel.setTextFormat(Qt.TextFormat.RichText)
        self.TextLabel.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.AcceptButton = QPushButton(accept_text)
        self.CancelButton = QPushButton(cancel_text)

        self.TextLayout = QHBoxLayout()
        self.TextLayout.setContentsMargins(4, 4, 6, 0)
        self.ButtonsLayout = QHBoxLayout()
        self.ButtonsLayout.setContentsMargins(0, 0, 0, 0)

        if cancel_text is None:
            self.CancelButton.hide()
        else:
            self.CancelButton.setText(cancel_text)

        if self.AcceptButton.sizeHint().width() > self.CancelButton.sizeHint().width():
            width = self.AcceptButton.sizeHint().width()
        else:
            width = self.CancelButton.sizeHint().width()

        self.AcceptButton.setFixedWidth(width + 16)
        self.CancelButton.setFixedWidth(width + 16)

        self.AcceptButton.clicked.connect(self.accept)
        self.CancelButton.clicked.connect(self.cancel)

        self.TextLayout.addWidget(self.IconLabel)
        self.TextLayout.addSpacing(12)
        self.TextLayout.addWidget(self.TextLabel)
        self.ButtonsLayout.addWidget(self.AcceptButton, alignment=Qt.AlignmentFlag.AlignRight, stretch=1)
        self.ButtonsLayout.addWidget(self.CancelButton)

        self.CentralLayout.addLayout(self.TextLayout)
        self.CentralLayout.addLayout(self.ButtonsLayout)

        self.show()

    def accept(self):
        self.accepted.emit()
        self.close()

    def cancel(self):
        self.cancelled.emit()
        self.close()
