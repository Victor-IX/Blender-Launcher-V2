from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

if TYPE_CHECKING:
    from datetime import datetime


DATETIME_FORMAT = "%d %b %Y, %H:%M"


class DateTimeWidget(QPushButton):
    left_arrow = "◂"
    right_arrow = "▸"

    def __init__(self, dt: datetime, build_hash: str | None, parent=None):
        super().__init__(parent)
        self.build_hash = build_hash

        self.setProperty("TextOnly", True)

        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.datetimeStr = dt.strftime(DATETIME_FORMAT)
        self.datetimeLabel = QLabel(self.datetimeStr)
        self.datetimeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.font_metrics = self.datetimeLabel.fontMetrics()

        # Set fixed width to match header width (118px from base_page_widget.py)
        self.setFixedWidth(118)

        if self.build_hash is not None:
            self.LeftArrowLabel = QLabel(self.left_arrow)
            self.LeftArrowLabel.setVisible(False)
            self.RightArrowLabel = QLabel(self.right_arrow)
            self.RightArrowLabel.setVisible(False)

            self.BuildHashLabel = QLabel(self.build_hash)
            self.BuildHashLabel.hide()
            self.BuildHashLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.layout.addWidget(self.LeftArrowLabel)
            self.layout.addWidget(self.datetimeLabel, stretch=1)
            self.layout.addWidget(self.BuildHashLabel, stretch=1)
            self.layout.addWidget(self.RightArrowLabel)

            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Press to show build hash number")
            self.clicked.connect(self.toggle_visibility)
        else:
            self.datetimeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.datetimeLabel, stretch=1)

    def toggle_visibility(self):
        self.datetimeLabel.setVisible(not self.datetimeLabel.isVisible())
        self.BuildHashLabel.setVisible(not self.BuildHashLabel.isVisible())

        if self.BuildHashLabel.isVisible():
            self.setToolTip("Press to show date and time")
        else:
            self.setToolTip("Press to show build hash number")

    def enterEvent(self, event: QEvent) -> None:
        if self.build_hash is not None:
            self.LeftArrowLabel.setVisible(True)
            self.RightArrowLabel.setVisible(True)

        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        if self.build_hash is not None:
            self.LeftArrowLabel.setVisible(False)
            self.RightArrowLabel.setVisible(False)

        return super().leaveEvent(event)
