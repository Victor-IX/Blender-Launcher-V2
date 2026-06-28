import shlex
import subprocess
import sys
from pathlib import Path
from subprocess import DEVNULL, PIPE, STDOUT

from modules.platform_utils import get_platform
from PySide6.QtCore import QThread

if sys.platform == "win32":
    from subprocess import CREATE_NO_WINDOW

_MACOS_PATHS_D_FILE = "/etc/paths.d/blender-launcher"


class Register(QThread):
    def __init__(self, path):
        QThread.__init__(self)
        self.path = path

    def run(self):
        platform = get_platform()

        if platform == "Windows":
            b3d_exe = Path(self.path) / "blender.exe"
            subprocess.call(
                [str(b3d_exe), "-r"],
                creationflags=CREATE_NO_WINDOW,
                shell=True,
                stdout=PIPE,
                stderr=STDOUT,
                stdin=DEVNULL,
            )
        elif platform == "Linux":
            b3d_exe = Path(self.path) / "blender"
        elif platform == "macOS":
            macos_dir = _find_macos_dir(Path(self.path))
            if macos_dir is not None:
                _write_paths_d(str(macos_dir))


def _find_macos_dir(path: Path) -> Path | None:
    """Find the Contents/MacOS directory inside the Blender .app bundle."""
    candidates = [
        path / "Blender.app" / "Contents" / "MacOS",
        path / "Blender" / "Blender.app" / "Contents" / "MacOS",
        path / "Bforartists.app" / "Contents" / "MacOS",
        path / "Bforartists" / "Bforartists.app" / "Contents" / "MacOS",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _write_paths_d(macos_dir: str) -> None:
    """Write the Blender binary directory to /etc/paths.d/blender-launcher via osascript."""
    shell_cmd = f"echo {shlex.quote(macos_dir)} > {_MACOS_PATHS_D_FILE}"
    applescript_str = shell_cmd.replace("\\", "\\\\").replace('"', '\\"')
    script = f'do shell script "{applescript_str}" with administrator privileges'
    subprocess.call(["osascript", "-e", script], stdout=PIPE, stderr=STDOUT)
