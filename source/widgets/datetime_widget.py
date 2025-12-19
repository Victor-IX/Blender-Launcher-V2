from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

DATETIME_FORMAT = "%d %b %Y, %H:%M"


def get_relative_time(dt: datetime) -> str:
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

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
    # Reserve space for arrows when they appear on hover
    ARROW_RESERVE_WIDTH = 20

    # Display modes
    MODE_RELATIVE = 0
    MODE_HASH = 1
    MODE_EXACT = 2

    def __init__(self, dt: datetime, build_hash: str | None, parent=None):
        super().__init__(parent)
        self.build_hash = build_hash
        self._display_mode = self.MODE_RELATIVE

        self.setProperty("TextOnly", True)

        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.layout.setSpacing(0)

        self.datetimeStr = dt.strftime(DATETIME_FORMAT)
        self.relativeTimeStr = get_relative_time(dt)
        self._buildHashStr = build_hash or ""

        self.displayLabel = QLabel()
        self.displayLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.displayLabel.setStyleSheet("color: #808080;")
        self.font_metrics = QFontMetrics(self.displayLabel.font())

        # Set fixed width to match header width (118px from base_page_widget.py)
        self.setFixedWidth(118)

        if self.build_hash is not None:
            self.LeftArrowLabel = QLabel(self.left_arrow)
            self.LeftArrowLabel.setVisible(False)
            self.RightArrowLabel = QLabel(self.right_arrow)
            self.RightArrowLabel.setVisible(False)

            self.layout.addWidget(self.LeftArrowLabel)
            self.layout.addWidget(self.displayLabel, stretch=1)
            self.layout.addWidget(self.RightArrowLabel)

            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.clicked.connect(self.cycle_display_mode)
        else:
            self.displayLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.displayLabel, stretch=1)

        # Set initial elided text and tooltip
        self._update_elided_text()
        self._update_tooltip()

    def cycle_display_mode(self):
        """Cycle through display modes: relative time -> hash -> exact datetime."""
        self._display_mode = (self._display_mode + 1) % 3
        self._update_elided_text()
        self._update_tooltip()

    def _update_tooltip(self):
        """Update tooltip based on current display mode."""
        if self.build_hash is None:
            self.setToolTip(f"Exact time: {self.datetimeStr}")
            return

        if self._display_mode == self.MODE_RELATIVE:
            self.setToolTip(f"Exact time: {self.datetimeStr}\nClick to show build hash")
        elif self._display_mode == self.MODE_HASH:
            self.setToolTip(f"Exact time: {self.datetimeStr}\nClick to show exact date")
        else:  # MODE_EXACT
            self.setToolTip(f"Build hash: {self._buildHashStr}\nClick to show relative time")

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        """Update label text with eliding to fit available width."""
        # Calculate available width for text (reserve space for arrows on hover and margins)
        margins = self.layout.contentsMargins()
        available_width = self.width() - self.ARROW_RESERVE_WIDTH - margins.left() - margins.right()

        # Get the text to display based on current mode
        if self._display_mode == self.MODE_RELATIVE:
            text = self.relativeTimeStr
        elif self._display_mode == self.MODE_HASH:
            text = self._buildHashStr
        else:  # MODE_EXACT
            text = self.datetimeStr

        # Elide the text to fit
        elided_text = self.font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
        self.displayLabel.setText(elided_text)
