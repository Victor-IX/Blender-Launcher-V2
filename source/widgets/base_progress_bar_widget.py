from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QProgressBar


class BaseProgressBarWidget(QProgressBar):
    progress_updated = Signal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.title = ""

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimum(0)
        self.set_progress(0, 0)

    def set_title(self, title: str):
        self.title = title
        self.setFormat(f"{self.title}: {self.last_progress[0]:.1f} of {self.last_progress[1]:.1f} MB")

    @Slot(int, int)
    def set_progress(self, obtained: int | float, total: int | float, title: str | None = None):
        if title is not None and title != self.title:
            self.title = title

        # Update appearance
        self.setMaximum(int(total))
        self.setValue(int(obtained))

        # Convert bytes to megabytes
        obtained = obtained / 1048576
        total = total / 1048576

        # Repaint and call signal
        self.setFormat(f"{self.title}: {obtained:.1f} of {total:.1f} MB")
        self.progress_updated.emit(obtained, total)
        self.last_progress = (obtained, total)
