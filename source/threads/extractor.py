import logging
import re
import tarfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from send2trash import send2trash

from modules._platform import _check_call, _check_output
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

    if suffixes[-1] == ".dmg":
        # Mount the DMG and get the mount point
        mount_output = _check_output(["hdiutil", "mount", source.as_posix()]).decode("utf-8")

        # Extract mount point from hdiutil output
        # Output format: /dev/disk14s1    Apple_HFS    /Volumes/Bforartists 1
        mount_point = None
        for line in mount_output.strip().split("\n"):
            if "/Volumes/" in line:
                # Get the last field which is the mount point
                match = re.search(r"/Volumes/.*$", line)
                if match:
                    mount_point = match.group(0).strip()
                    break

        if mount_point is None:
            raise RuntimeError(f"Failed to determine mount point for {source}")

        try:
            mount_path = Path(mount_point)

            # Find .app file in the mounted volume
            app_files = list(mount_path.glob("*.app"))

            if not app_files:
                raise RuntimeError(f"No .app file found in {mount_point}")

            app_file = app_files[0]

            # Calculate approximate size for progress reporting
            # Note: This is approximate as we use ditto which doesn't provide progress
            total_size = sum(f.stat().st_size for f in app_file.rglob("*") if f.is_file())
            progress_callback(0, total_size)

            # Create destination directory
            dist = destination / source.stem
            if not dist.is_dir():
                dist.mkdir(parents=True)

            # Copy the .app bundle to destination using ditto
            # ditto is the recommended way to copy .app bundles on macOS
            # as it preserves resource forks, extended attributes, and permissions
            dest_app = dist / app_file.name

            logger.info(f"Copying {app_file} to {dest_app} using ditto")
            try:
                _check_call(["ditto", app_file.as_posix(), dest_app.as_posix()])
                logger.info(f"Successfully copied {app_file.name} to {dest_app}")
            except Exception as e:
                logger.error(f"Failed to copy {app_file} with ditto: {e}")
                raise

            # Report completion
            progress_callback(total_size, total_size)
            logger.info(f"DMG extraction completed, returning {dist}")

            return dist
        finally:
            # Always unmount the DMG, even if an error occurred
            try:
                logger.info(f"Unmounting {mount_point}")
                _check_call(["hdiutil", "unmount", mount_point])
                logger.info(f"Successfully unmounted {mount_point}")
            except Exception as e:
                logger.warning(f"Failed to unmount {mount_point}: {e}")
                # Try force unmount as fallback
                try:
                    logger.info(f"Attempting force unmount of {mount_point}")
                    _check_call(["hdiutil", "unmount", "-force", mount_point])
                    logger.info(f"Successfully force unmounted {mount_point}")
                except Exception as e2:
                    logger.error(f"Force unmount also failed: {e2}")
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
