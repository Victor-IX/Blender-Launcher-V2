from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime, timezone

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy

if TYPE_CHECKING:
    pass


DATETIME_FORMAT = "%d %b %Y, %H:%M"


def get_relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} min{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds // 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds // 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(seconds // 31536000)
        return f"{years} year{'s' if years > 1 else ''} ago"


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
        self.relativeTimeStr = get_relative_time(dt)
        
        self.datetimeLabel = QLabel(self.relativeTimeStr)
        self.datetimeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.datetimeLabel.setStyleSheet("color: #808080;")  # Lighter grey for secondary text
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
            self.setToolTip(f"Exact time: {self.datetimeStr}\nPress to show build hash number")
            self.clicked.connect(self.toggle_visibility)
        else:
            self.datetimeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.datetimeLabel, stretch=1)
            self.setToolTip(f"Exact time: {self.datetimeStr}")

    def toggle_visibility(self):
        self.datetimeLabel.setVisible(not self.datetimeLabel.isVisible())
        self.BuildHashLabel.setVisible(not self.BuildHashLabel.isVisible())

        if self.BuildHashLabel.isVisible():
            self.setToolTip(f"Exact time: {self.datetimeStr}\nPress to show relative time")
        else:
            self.setToolTip(f"Exact time: {self.datetimeStr}\nPress to show build hash number")

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
