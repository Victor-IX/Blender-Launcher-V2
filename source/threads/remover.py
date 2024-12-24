from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from modules.task import Task
from PySide6.QtCore import Signal
from send2trash import send2trash


@dataclass
class RemovalTask(Task):
    path: Path
    trash: bool = True
    finished = Signal(bool)

    def run(self):
        try:
            if self.trash:
                send2trash(str(self.path))
            else:
                if self.path.is_dir():
                    rmtree(self.path.as_posix())
                else:
                    self.path.unlink()

            self.finished.emit(0)
        except OSError:
            self.finished.emit(1)
            raise

    def __str__(self):
        return f"Remove {self.path}"
