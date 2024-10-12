from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from modules._platform import get_platform
from modules.prefs_info import PreferenceInfo, read_prefs
from modules.settings import get_library_folder
from modules.task import Task
from PyQt5.QtCore import pyqtSignal

if TYPE_CHECKING:
    from collections.abc import Iterable


def get_blender_builds(folders: Iterable[str | Path]) -> Iterable[tuple[Path, bool]]:
    """Finds blender builds in the library folder, given the subfolders to search in

    Parameters
    ----------
    folders : Iterable[str  |  Path]
        subfolders to search

    Returns
    -------
    Iterable[tuple[Path, bool]]
        an iterable of found builds and whether they're recognized as valid Blender builds
    """

    library_folder = get_library_folder()
    platform = get_platform()

    blender_exe = {
        "Windows": "blender.exe",
        "Linux": "blender",
        "macOS": "Blender/Blender.app/Contents/MacOS/Blender",
    }.get(platform, "blender")

    for folder in folders:
        path = library_folder / folder
        if path.is_dir():
            for build in path.iterdir():
                if build.is_dir():
                    yield (
                        folder / build,
                        ((folder / build / ".blinfo").is_file() or (path / build / blender_exe).is_file()),
                    )


@dataclass(frozen=True)
class DrawLibraryTask(Task):
    folders: Iterable[str | Path] = ("stable", "daily", "experimental", "custom")
    found = pyqtSignal(Path)
    unrecognized = pyqtSignal(Path)
    finished = pyqtSignal()

    def run(self):
        for build, recognized in get_blender_builds(folders=self.folders):
            if recognized:
                self.found.emit(build)
            else:
                self.unrecognized.emit(build)

        self.finished.emit()

    def __str__(self):
        return f"Draw libraries {self.folders}"


def get_prefs(folder: Path) -> Iterable[PreferenceInfo]:
    for subfolder in folder.iterdir():
        if not subfolder.is_dir():
            continue

        yield read_prefs(subfolder)


@dataclass(frozen=True)
class DrawPreferencesTask(Task):
    folder: Path
    found = pyqtSignal(PreferenceInfo)
    finished = pyqtSignal()

    def run(self):
        for c in get_prefs(self.folder):
            self.found.emit(c)
        self.finished.emit()
