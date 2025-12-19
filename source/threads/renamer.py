import logging

from dataclasses import dataclass
from pathlib import Path

from modules.task import Task
from PySide6.QtCore import Signal
from send2trash import send2trash

logger = logging.getLogger()


@dataclass
class RenameTask(Task):
    src: Path
    dst_name: str

    finished = Signal(Path, bool)
    failure = Signal()

    def run(self):
        is_removed = False

        try:
            dst = self.src.parent / self.dst_name.lower().replace(" ", "-")

            if dst.exists():
                is_removed = True
                send2trash(dst)
                logger.debug(f"Removed existing file: {dst}")

            self.src.rename(dst)
            self.finished.emit(dst, is_removed)
        except OSError:
            self.failure.emit()
            raise

    def __str__(self):
        return f"Rename {self.src} to {self.dst_name}"
