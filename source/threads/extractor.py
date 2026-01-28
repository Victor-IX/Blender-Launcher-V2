import logging
import re
import shutil
import tarfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import py7zr
from modules._platform import _check_call, _check_output
from modules.enums import MessageType
from modules.task import Task
from PySide6.QtCore import Signal
from send2trash import send2trash

logger = logging.getLogger()


def extract(source: Path, destination: Path, progress_callback: Callable[[int, int], None]) -> Path | None:
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

                # Check if this is a UPBGE archive (folder is "bin" with bin/Release structure)
                is_upbge = folder == "bin" and any(n.startswith("bin/Release/") for n in names)

                if is_upbge:
                    folder = source.stem
                    logger.info(f"Detected UPBGE archive with bin/Release structure, using: {folder}")
                elif folder is None:
                    folder = members[0].filename.split("/")[0]

                uncompress_size = sum(member.file_size for member in members)
                progress_callback(0, uncompress_size)
                extracted_size = 0

                # For UPBGE flat archives, extract into a subfolder
                extract_dest = destination / folder if is_upbge else destination

                for member in members:
                    zf.extract(member, extract_dest)
                    extracted_size += member.file_size
                    progress_callback(extracted_size, uncompress_size)
            return destination / folder
        except zipfile.BadZipFile as e:
            logger.error(f"Bad zip file: {source} - {e}")
            raise

    if suffixes[-1] == ".7z":
        try:
            with py7zr.SevenZipFile(source, mode="r") as szf:
                allfiles = szf.getnames()
                folder = _get_build_folder(allfiles)

                # Check if this is a UPBGE archive with bin/Release structure
                is_upbge = folder == "bin" and any(n.startswith("bin/Release/") for n in allfiles)

                if is_upbge:
                    folder = source.stem
                    logger.info(f"Detected UPBGE 7z archive with bin/Release structure, using: {folder}")
                elif folder is None:
                    folder = allfiles[0].split("/")[0]

                # For UPBGE flat archives, extract into a subfolder
                extract_dest = destination / folder if is_upbge else destination
                extract_dest.mkdir(parents=True, exist_ok=True)

                # Get file info for progress tracking
                file_info = szf.list()
                total_size = sum(f.uncompressed for f in file_info)
                progress_callback(0, total_size)

                # Extract all files
                szf.extractall(path=extract_dest)

                # Report completion
                progress_callback(total_size, total_size)

            return destination / folder
        except py7zr.Bad7zFile as e:
            logger.error(f"Bad 7z file: {source} - {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to extract 7z file: {source} - {e}")
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

            # Find all .app files in the mounted volume (e.g., UPBGE has Blender.app and Blenderplayer.app)
            app_files = list(mount_path.glob("*.app"))

            if not app_files:
                raise RuntimeError(f"No .app file found in {mount_point}")

            # Calculate approximate total size for progress reporting
            total_size = sum(f.stat().st_size for app_file in app_files for f in app_file.rglob("*") if f.is_file())
            progress_callback(0, total_size)

            # Create destination directory
            dist = destination / source.stem
            if not dist.is_dir():
                dist.mkdir(parents=True)

            # Copy all .app bundles to destination using ditto
            # ditto is the recommended way to copy .app bundles on macOS
            # as it preserves resource forks, extended attributes, and permissions
            copied_size = 0
            for app_file in app_files:
                dest_app = dist / app_file.name

                logger.info(f"Copying {app_file} to {dest_app} using ditto")
                try:
                    _check_call(["ditto", app_file.as_posix(), dest_app.as_posix()])
                    logger.info(f"Successfully copied {app_file.name} to {dest_app}")

                    # Verify the copy was successful by checking if the destination exists
                    if not dest_app.exists():
                        raise RuntimeError(f"Copy completed but destination not found: {dest_app}")

                    # Remove quarantine attribute to allow unsigned apps (like UPBGE) to run
                    try:
                        _check_call(["xattr", "-cr", dest_app.as_posix()])
                        logger.info(f"Removed quarantine attribute from {dest_app}")
                    except Exception as e:
                        logger.warning(f"Failed to remove quarantine attribute: {e}")

                    # Update progress
                    app_size = sum(f.stat().st_size for f in app_file.rglob("*") if f.is_file())
                    copied_size += app_size
                    progress_callback(copied_size, total_size)

                except Exception as e:
                    logger.error(f"Failed to copy {app_file} with ditto: {e}")
                    raise

            # On macOS, ensure file system buffers are flushed
            _check_call(["sync"])
            logger.info("File system buffers flushed")

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


def _get_build_folder(names: list[str]):
    tops = {n.split("/")[0] for n in names if n and "/" in n}
    folders = {t for t in tops if any(n.startswith(f"{t}/") for n in names)}

    if len(folders) == 1:
        return next(iter(folders))

    return None


def _fix_upbge_structure(build_path: Path) -> Path:
    """
    Fix UPBGE build structure by moving contents to the expected location.

    UPBGE builds can have different structures:
    1. bin/Release subfolder (daily builds): needs to be flattened
    2. Nested folder with same name as zip (stable builds): needs unwrapping

    Args:
        build_path: Path to extracted build folder

    Returns:
        Path to the fixed build folder (may differ from input)
    """
    # Handle bin/Release structure (daily builds)
    bin_release = build_path / "bin" / "Release"

    if bin_release.exists():
        logger.info(f"Detected UPBGE bin/Release structure in {build_path}")

        try:
            # Move all contents from bin/Release to build root
            for item in bin_release.iterdir():
                dest = build_path / item.name
                if dest.exists():
                    # If destination exists, remove it first
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(build_path))
                logger.debug(f"Moved {item.name} to build root")

            # Remove the now-empty bin directory
            bin_folder = build_path / "bin"
            if bin_folder.exists():
                shutil.rmtree(bin_folder)
                logger.info(f"Removed empty bin folder from {build_path}")

            logger.info(f"Successfully fixed UPBGE bin/Release structure for {build_path}")
        except Exception as e:
            logger.error(f"Failed to fix UPBGE structure: {e}")
            raise

        return build_path

    # Handle nested folder structure (stable builds)
    # Check if there's a single subfolder with the same name as the build
    subdirs = [d for d in build_path.iterdir() if d.is_dir()]

    # Look for UPBGE executable to determine if unwrapping is needed
    # UPBGE uses blender.exe/blender as executable name, not upbge.exe/upbge
    has_upbge_exe = (build_path / "blender.exe").exists() or (build_path / "blender").exists()

    if not has_upbge_exe and len(subdirs) == 1:
        nested_folder = subdirs[0]
        nested_has_upbge = (nested_folder / "blender.exe").exists() or (nested_folder / "blender").exists()

        if nested_has_upbge:
            logger.info(f"Detected UPBGE nested folder structure: {nested_folder.name} inside {build_path.name}")

            try:
                # Move all contents from nested folder up one level
                temp_dir = build_path.parent / f"{build_path.name}_temp"
                shutil.move(str(nested_folder), str(temp_dir))

                # Remove the now-empty parent folder
                shutil.rmtree(build_path)

                # Rename temp folder to the original name
                shutil.move(str(temp_dir), str(build_path))

                logger.info(f"Successfully unwrapped UPBGE nested structure for {build_path}")
            except Exception as e:
                logger.error(f"Failed to unwrap UPBGE nested structure: {e}")
                raise

    return build_path


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
            if result is None:
                raise ValueError(f"Unsupported archive format: {self.file.suffix}")

            # Fix UPBGE structure if needed
            result = _fix_upbge_structure(result)
            self.finished.emit(result, is_removed)
        except (zipfile.BadZipFile, tarfile.TarError, py7zr.Bad7zFile) as e:
            self._handle_extraction_error(e)
        except Exception as e:
            self._handle_extraction_error(e, use_exception_log=True)

    def __str__(self):
        return f"Extract {self.file} to {self.destination}"
