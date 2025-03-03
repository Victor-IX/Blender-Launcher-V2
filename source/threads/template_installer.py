from dataclasses import dataclass
from pathlib import Path
from re import match
from shutil import copytree

from modules.settings import get_library_folder
from modules.task import Task
from PySide6.QtCore import Signal


def install_template(dist: Path):
    library_folder = Path(get_library_folder())
    template = library_folder / "template"

    template.mkdir(exist_ok=True)

    for directory in dist.iterdir():
        if match(r"\d+\.\d+.*", directory.name) is not None:
            copytree(
                src=template.as_posix(),
                dst=directory.as_posix(),
                dirs_exist_ok=True,
            )
            return


@dataclass
class TemplateTask(Task):
    destination: Path

    finished = Signal()

    def run(self):
        install_template(self.destination)
        self.finished.emit()

    def __str__(self):
        return f"Install template to {self.destination}"
