import logging
import time
from dataclasses import dataclass
from pathlib import Path

from modules.task import Task
from PySide6.QtCore import Signal
from send2trash import send2trash

logger = logging.getLogger()

_RENAME_MAX_RETRIES = 10
_RENAME_RETRY_DELAY = 0.5


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

            # Attempt to rename with retries in case of PermissionError
            # Renaming is likely to fail on Enterprise Windows Workstation
            # due to antivirus or other processes locking the file
            last_error: OSError | None = None
            for attempt in range(_RENAME_MAX_RETRIES):
                try:
                    self.src.rename(dst)
                    break
                except PermissionError as e:
                    last_error = e
                    logger.warning(f"Rename attempt {attempt + 1}/{_RENAME_MAX_RETRIES} failed: {e}")
                    time.sleep(_RENAME_RETRY_DELAY)
            else:
                raise last_error  # type: ignore[misc]

            self.finished.emit(dst, is_removed)
        except OSError:
            self.failure.emit()
            raise

    def __str__(self):
        return f"Rename {self.src} to {self.dst_name}"
