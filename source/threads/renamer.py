from dataclasses import dataclass
from pathlib import Path

from modules.task import Task
from PySide6.QtCore import Signal
from send2trash import send2trash


@dataclass
class RenameTask(Task):
    src: Path
    dst_name: str

    finished = Signal(Path)
    failure = Signal()

    def run(self):
        try:
            dst = self.src.parent / self.dst_name.lower().replace(" ", "-")

            if dst.exists():
                send2trash(dst)

            self.src.rename(dst)
            self.finished.emit(dst)
        except OSError:
            self.failure.emit()
            raise

    def __str__(self):
        return f"Rename {self.src} to {self.dst_name}"
