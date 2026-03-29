import logging
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from modules.settings import get_library_folder
from modules.task import Task
from PySide6.QtCore import Signal
from send2trash import send2trash

logger = logging.getLogger()


def purge_temp_folder():
    """Purge all files in the temp folder."""
    temp_folder = Path(get_library_folder()) / ".temp"
    if temp_folder.exists() and temp_folder.is_dir():
        try:
            for item in temp_folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    rmtree(item)
            return True
        except Exception:
            return False
    return True


@dataclass
class RemovalTask(Task):
    path: Path
    trash: bool = True
    finished = Signal(bool)

    def run(self):
        try:
            if not self.path.exists():
                self.finished.emit(0)
                logger.info(f"Path {self.path} does not exist, nothing to remove.")
                return
            if self.trash:
                send2trash(self.path)
            else:
                if self.path.is_dir():
                    rmtree(self.path)
                else:
                    self.path.unlink()

            self.finished.emit(0)
        except OSError:
            self.finished.emit(1)
            raise

    def __str__(self):
        return f"Remove {self.path}"
