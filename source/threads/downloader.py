import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modules._copyfileobj import copyfileobj
from modules.connection_manager import REQUEST_MANAGER
from modules.enums import MessageType
from modules.settings import get_library_folder
from modules.string_utils import extract_filename_from_url
from modules.task import Task
from PySide6.QtCore import Signal
from threads.scraping.bfa import BFA_NC_BASE_URL, BFA_NC_WEBDAV_SHARE_TOKEN
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


def convert_nextcloud_share_to_webdav(url: str) -> str | None:
    """Convert Nextcloud share download URL to WebDAV URL.

    Converts:
    https://cloud.bforartists.de/index.php/s/{token}/download?path={path}&files={filename}
    To:
    https://cloud.bforartists.de/public.php/webdav{path}/{filename}
    """
    try:
        parsed = urlparse(url)

        # Check if it's a Nextcloud share download URL
        if "/index.php/s/" not in parsed.path or "/download" not in parsed.path:
            return None

        # Parse query parameters
        params = parse_qs(parsed.query)
        path = params.get("path", [""])[0]
        files = params.get("files", [""])[0]

        if not files:
            logger.warning(f"No 'files' parameter found in URL: {url}")
            return None

        # Construct WebDAV URL
        # public.php/webdav{path}/{filename}
        webdav_path = f"{path}/{files}" if path else f"/{files}"
        webdav_url = f"{BFA_NC_BASE_URL}/public.php/webdav{webdav_path}"

        logger.info(f"Converted share URL to WebDAV: {url} -> {webdav_url}")
        return webdav_url
    except Exception as e:
        logger.exception(f"Failed to convert URL to WebDAV format: {e}")
        return None


@dataclass
class DownloadTask(Task):
    manager: REQUEST_MANAGER
    link: str
    progress = Signal(int, int)
    finished = Signal(Path)

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
            file_path.unlink()
            logger.debug(f"Cleaned up file: {file_path}")

    def run(self):
        self.progress.emit(0, 0)
        temp_folder = Path(get_library_folder()) / ".temp"
        temp_folder.mkdir(exist_ok=True)
        filename = extract_filename_from_url(self.link)
        dist = temp_folder / filename
        headers = {}

        # Convert Nextcloud share URLs to WebDAV format
        download_url = self.link
        if "cloud.bforartists.de" in self.link and "/index.php/s/" in self.link:
            webdav_url = convert_nextcloud_share_to_webdav(self.link)
            if webdav_url:
                download_url = webdav_url

        # Apply authentication for Nextcloud WebDAV endpoints
        is_nextcloud = "cloud.bforartists.de" in download_url and (
            "public.php/webdav" in download_url or "public.php/dav" in download_url
        )
        if is_nextcloud:
            auth_string = base64.b64encode(f"{BFA_NC_WEBDAV_SHARE_TOKEN}:".encode()).decode("ascii")
            headers["Authorization"] = f"Basic {auth_string}"
            logger.info(f"Applying Nextcloud authentication for: {download_url}")

        # Download the file
        try:
            with self.manager.request("GET", download_url, preload_content=False, timeout=10, headers=headers) as r:
                logger.debug(f"Response headers: {dict(r.headers)}")

                if not self._validate_response(r):
                    return

                self._download(r, dist)
        except MaxRetryError as e:
            logger.exception(f"Requesting is taking longer than usual! {e}")
            self.message.emit("Requesting is taking longer than usual! see debug logs for more.", MessageType.ERROR)
            # Retry once
            try:
                with self.manager.request("GET", download_url, preload_content=False, headers=headers) as r:
                    if not self._validate_response(r, context="Retry "):
                        self._cleanup_file(dist)
                        return
                    self._download(r, dist)
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
