import base64
import logging

from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Signal
from urllib3.exceptions import MaxRetryError

from modules._copyfileobj import copyfileobj
from modules.connection_manager import REQUEST_MANAGER
from modules.enums import MessageType
from modules.settings import get_library_folder
from modules.string_utils import extract_filename_from_url
from modules.task import Task
from threads.scraper import BFA_NC_WEBDAV_SHARE_TOKEN

logger = logging.getLogger()


@dataclass
class DownloadTask(Task):
    manager: REQUEST_MANAGER
    link: str
    progress = Signal(int, int)
    finished = Signal(Path)

    def run(self):
        self.progress.emit(0, 0)
        temp_folder = Path(get_library_folder()) / ".temp"
        temp_folder.mkdir(exist_ok=True)
        filename = extract_filename_from_url(self.link)
        dist = temp_folder / filename
        headers = {}

        if "cloud.bforartists.de/public.php/webdav" in self.link:
            auth_string = base64.b64encode(f"{BFA_NC_WEBDAV_SHARE_TOKEN}:".encode()).decode("ascii")
            headers["Authorization"] = f"Basic {auth_string}"

        try:
            with self.manager.request("GET", self.link, preload_content=False, timeout=10, headers=headers) as r:
                self._download(r, dist)
        except MaxRetryError as e:
            logger.exception(f"Requesting is taking longer than usual! {e}")
            self.message.emit("Requesting is taking longer than usual! see debug logs for more.", MessageType.ERROR)
            with self.manager.request("GET", self.link, preload_content=False, headers=headers) as r:
                self._download(r, dist)

        self.finished.emit(dist)

    def _download(self, r, dist: Path):
        size = int(r.headers["Content-Length"])
        with dist.open("wb") as f:
            copyfileobj(r, f, lambda x: self.progress.emit(x, size))

    def __str__(self):
        return f"Download {self.link}"
