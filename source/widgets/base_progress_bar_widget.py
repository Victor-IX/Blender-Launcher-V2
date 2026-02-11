from __future__ import annotations

from enum import Enum

from i18n import t
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QProgressBar


class BarState(Enum):
    DOWNLOADING = "act.prog.downloading"
    EXTRACTING = "act.prog.extracting"
    NONE = ""


class BaseProgressBarWidget(QProgressBar):
    progress_updated = Signal(int, int)

    State = BarState

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state = BarState.NONE
        self.title = ""

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimum(0)
        self.set_progress(0, 0)

    def set_state(self, state: BarState):
        self.state = state
        self.title = t(state.value)
        self.setFormat(
            t(
                "act.prog.pregress",
                title=self.title,
                progress=f"{self.last_progress[0]:.1f}",
                total=f"{self.last_progress[1]:.1f}",
            )
        )

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
        self.setFormat(
            t(
                "act.prog.pregress",
                title=self.title,
                progress=f"{obtained:.1f}",
                total=f"{total:.1f}",
            )
        )
        self.progress_updated.emit(obtained, total)
        self.last_progress = (obtained, total)
