import logging
import tarfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from send2trash import send2trash

from modules._platform import _check_call
from modules.enums import MessageType
from modules.task import Task
from PySide6.QtCore import Signal

logger = logging.getLogger()


def extract(source: Path, destination: Path, progress_callback: Callable[[int, int], None]) -> Optional[Path]:
    progress_callback(0, 0)
    suffixes = source.suffixes
    if suffixes[-1] == ".zip":
        # Validate zip file before attempting extraction
        if not zipfile.is_zipfile(source):
            error_msg = f"File is not a valid zip file: {source}"
            logger.error(error_msg)
            raise zipfile.BadZipFile(error_msg)

        try:
            with zipfile.ZipFile(source) as zf:
                members = zf.infolist()
                names = [m.filename for m in members]
                folder = _get_build_folder(names)

                if folder is None:
                    folder = members[0].filename.split("/")[0]

                uncompress_size = sum(member.file_size for member in members)
                progress_callback(0, uncompress_size)
                extracted_size = 0

                for member in members:
                    zf.extract(member, destination)
                    extracted_size += member.file_size
                    progress_callback(extracted_size, uncompress_size)
            return destination / folder
        except zipfile.BadZipFile as e:
            logger.error(f"Bad zip file: {source} - {e}")
            raise

    if suffixes[-2] == ".tar":
        with tarfile.open(source) as tar:
            members = tar.getmembers()
            names = [m.name for m in members]
            folder = _get_build_folder(names)

            if folder is None:
                folder = tar.getnames()[0].split("/")[0]

            uncompress_size = sum(member.size for member in members)
            progress_callback(0, uncompress_size)
            extracted_size = 0

            for member in members:
                tar.extract(member, path=destination)
                extracted_size += member.size
                progress_callback(extracted_size, uncompress_size)
        return destination / folder

    # TODO: Make sure this work with Bforartists with the patch note .txt file
    if suffixes[-1] == ".dmg":
        _check_call(["hdiutil", "mount", source.as_posix()])
        dist = destination / source.stem

        if not dist.is_dir():
            dist.mkdir()

        if "bforartists" in source.stem.lower():
            app_name = "Bforartists"
        else:
            app_name = "Blender"

        _check_call(["cp", "-R", f"/Volumes/{app_name}", dist.as_posix()])
        _check_call(["hdiutil", "unmount", f"/Volumes/{app_name}"])

        return dist
    return None


def _get_build_folder(names: List[str]):
    tops = {n.split("/")[0] for n in names if n and "/" in n}
    folders = {t for t in tops if any(n.startswith(f"{t}/") for n in names)}

    if len(folders) == 1:
        return next(iter(folders))

    return None


@dataclass
class ExtractTask(Task):
    file: Path
    destination: Path

    progress = Signal(int, int)
    finished = Signal(Path, bool)

    def _handle_extraction_error(self, error: Exception, use_exception_log: bool = False):
        """Handle extraction errors with cleanup."""
        error_msg = f"Extraction failed: {error}"
        if use_exception_log:
            logger.exception(error_msg)
        else:
            logger.error(error_msg)
        self.message.emit(error_msg, MessageType.ERROR)

        # Clean up corrupted file
        if self.file.exists():
            logger.info(f"Removing corrupted file: {self.file}")
            self.file.unlink()

    def run(self):
        is_removed = False
        try:
            if (self.destination / self.file.stem).exists():
                is_removed = True
                send2trash(self.destination / self.file.stem)
                logger.debug(f"Removed existing file: {self.destination / self.file.stem}")

            result = extract(self.file, self.destination, self.progress.emit)
            if result is not None:
                self.finished.emit(result, is_removed)
        except (zipfile.BadZipFile, tarfile.TarError) as e:
            self._handle_extraction_error(e)
            raise
        except Exception as e:
            self._handle_extraction_error(e, use_exception_log=True)
            raise

    def __str__(self):
        return f"Extract {self.file} to {self.destination}"
