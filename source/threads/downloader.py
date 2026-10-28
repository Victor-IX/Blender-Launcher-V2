import logging
from dataclasses import dataclass
from pathlib import Path

from modules._copyfileobj import copyfileobj
from modules.connection_manager import REQUEST_MANAGER
from modules.enums import MessageType
from modules.settings import get_library_folder
from modules.string_utils import extract_filename_from_url
from modules.task import Task
from PySide6.QtCore import Signal
from urllib3.exceptions import MaxRetryError

logger = logging.getLogger()

# Valid MIME types for archive files
VALID_ARCHIVE_TYPES = [
    "application/zip",
    "application/x-apple-diskimage",
    "application/x-zip-compressed",
    "application/octet-stream",
    "application/x-tar",
    "application/x-gzip",
    "application/x-xz",
    "application/gzip",
    "application/x-dmg",
]


@dataclass
class DownloadTask(Task):
    manager: REQUEST_MANAGER
    link: str
    progress = Signal(int, int)
    finished = Signal(Path)
    permission_error = Signal(str)

    def _validate_response(self, response, context: str = "") -> bool:
        """Validate HTTP response status and content type. Returns True if valid."""
        content_type = response.headers.get("Content-Type", "").lower()
        logger.info(f"{context}Response status: {response.status}, Content-Type: {content_type}")

        # Check HTTP status code
        if response.status >= 400:
            error_msg = f"Download failed: HTTP {response.status} for {self.link}"
            logger.error(error_msg)
            self.message.emit(error_msg, MessageType.ERROR)
            return False

        # Validate Content-Type for archive files
        if content_type and not any(vt in content_type for vt in VALID_ARCHIVE_TYPES):
            error_msg = f"Download failed: Unexpected content type '{content_type}' for {self.link}"
            logger.error(error_msg)
            logger.error(f"Valid types are: {', '.join(VALID_ARCHIVE_TYPES)}")
            self.message.emit(error_msg, MessageType.ERROR)
            return False

        return True

    def _cleanup_file(self, file_path: Path):
        """Clean up a file if it exists."""
        if file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Cleaned up file: {file_path}")
            except OSError:
                logger.exception(f"Failed to clean up file: {file_path}")

    def run(self):
        self.progress.emit(0, 0)
        temp_folder = Path(get_library_folder()) / ".temp"
        filename = extract_filename_from_url(self.link)
        dist = temp_folder / filename
        # Download the file
        try:
            temp_folder.mkdir(exist_ok=True)
            with self.manager.request("GET", self.link, preload_content=False, timeout=10) as r:
                logger.debug(f"Response headers: {dict(r.headers)}")

                if not self._validate_response(r):
                    return

                self._download(r, dist)
        except PermissionError:
            logger.exception(f"Permission denied writing to {dist}")
            self.permission_error.emit(str(temp_folder))
            return
        except MaxRetryError as e:
            logger.exception(f"Requesting is taking longer than usual! {e}")
            self.message.emit("Requesting is taking longer than usual! see debug logs for more.", MessageType.ERROR)
            # Retry once
            try:
                with self.manager.request("GET", self.link, preload_content=False) as r:
                    if not self._validate_response(r, context="Retry "):
                        self._cleanup_file(dist)
                        return
                    self._download(r, dist)
            except PermissionError:
                logger.exception(f"Permission denied writing to {dist}")
                self.permission_error.emit(str(temp_folder))
                return
            except Exception as retry_error:
                logger.exception(f"Retry failed: {retry_error}")
                self.message.emit(f"Download failed: {retry_error}", MessageType.ERROR)
                self._cleanup_file(dist)
                return
        except Exception as e:
            logger.exception(f"Download error: {e}")
            self.message.emit(f"Download failed: {e}", MessageType.ERROR)
            self._cleanup_file(dist)
            return

        self.finished.emit(dist)

    def _download(self, r, dist: Path):
        size = int(r.headers["Content-Length"])
        with dist.open("wb") as f:
            copyfileobj(r, f, lambda x: self.progress.emit(x, size))

    def __str__(self):
        return f"Download {self.link}"
