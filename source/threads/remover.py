import logging
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from modules.enums import MessageType
from modules.file_utils import retry_on_permission_error
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
                    retry_on_permission_error(item.unlink)
                elif item.is_dir():
                    retry_on_permission_error(rmtree, item)
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
                retry_on_permission_error(send2trash, self.path)
            else:
                if self.path.is_dir():
                    retry_on_permission_error(rmtree, self.path)
                else:
                    retry_on_permission_error(self.path.unlink)

            self.finished.emit(0)
        except OSError:
            logger.exception(f"Failed to remove {self.path}")
            self.message.emit(f"Failed to remove {self.path}", MessageType.ERROR)
            self.finished.emit(1)

    def __str__(self):
        return f"Remove {self.path}"
