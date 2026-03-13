import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self, TypedDict

from modules.connection_manager import ConnectionManager
from modules.platform_utils import labels_cache_path
from modules.task import Task
from PySide6.QtCore import QReadWriteLock, Signal

logger = logging.getLogger()


PAGE_SIZE = 50
PULLS_LINK = f"https://projects.blender.org/api/v1/repos/blender/blender/pulls?limit={PAGE_SIZE}&sort=recentupdate"
INDIVIDUAL_PULLS = "https://projects.blender.org/api/v1/repos/blender/blender/pulls/{}"
MAX_PAGE_REQUESTS = 4


class Pr(TypedDict):  # Only relevant fields
    number: int
    title: str


class PrLabelFetcher:
    def __init__(self, man: ConnectionManager):
        self.manager = man
        self.path = labels_cache_path()
        self._label_cache: LabelCache = LabelCache.try_from_file(self.path) or LabelCache()

    def fetch_one(self, pr: int) -> Pr | None:
        r = self.manager.request("GET", INDIVIDUAL_PULLS.format(pr))
        if r is None:
            logger.error(f"Failed to fetch PR {pr}")
            return None
        try:
            return json.loads(r.data)
        except json.JSONDecodeError as e:
            logger.exception(f"Invalid or broken JSON returned when fetching PR #{pr}: {e}")
            return None

    def fetch(self, page: int | None = None) -> list[Pr] | None:
        if page is not None:
            url = PULLS_LINK + f"&page={page}"
        else:
            url = PULLS_LINK

        r = self.manager.request("GET", url)
        if r is None:
            logger.error("Failed to fetch PR labels")
            return None

        return json.loads(r.data)

    def cache_latest_pages(self):
        for idx in range(MAX_PAGE_REQUESTS):
            d = self.fetch(idx)
            if d is None:
                break
            labels = _pr_labels(d)
            # if every label found in the current page has already been fetched, early exit
            if len(labels.keys() - self._label_cache.keys()) == 0:
                break

            self._label_cache.update(labels)

    def get_cached(self, x: int) -> str | None:
        return self._label_cache.get(x)

    def get(self, x: int) -> str | None:
        # check if we already know it
        if x in self._label_cache:
            return self._label_cache[x]

        logger.debug("PR {x} missing, searching...")

        pr = self.fetch_one(x)
        if pr is not None:
            self.__add_to_cache(x, pr["title"].strip())
            return self._label_cache[x]
        return None

    def __add_to_cache(self, x: int, v: str):
        self._label_cache[x] = v

    def save(self):
        self._label_cache.write(self.path)

    def __del__(self):
        self.save()


def _pr_labels(lst: list[Pr]) -> dict[int, str]:
    return {pr["number"]: pr["title"].strip() for pr in lst}


class LabelCache(dict[int, str]):
    _lock = QReadWriteLock()

    @classmethod
    def try_from_file(cls, file: Path) -> Self | None:
        cls._lock.lockForRead()
        f = cls._try_from_file(file)
        cls._lock.unlock()
        return f

    @classmethod
    def _try_from_file(cls, file: Path) -> Self | None:
        if not file.exists():
            logger.info(f"Cache file {file} does not exist, creating new cache")
            return None

        try:
            d = cls()
            with file.open("r", encoding="utf-8") as f:
                for line in f:
                    n, label = line.strip().split(":", 1)
                    d[int(n)] = label
            logger.debug(f"Loaded cache from {file}")
            return d
        except OSError as e:
            logger.exception(f"Failed to load cache {file}: {e}")
            return None

    def write(self, file: Path):
        # first, reread the file if it exists and union self and other
        other = self.try_from_file(file)
        if other is not None:
            self |= other

        # write the new cache down
        self._lock.lockForWrite()
        with file.open("w", encoding="utf-8") as f:
            for n, label in sorted(self.items()):
                f.write(f"{n}:{label.strip()}\n")
        self._lock.unlock()


@dataclass
class FetchPrTask(Task):
    number: int
    manager: ConnectionManager

    finished = Signal(str)

    def run(self):
        fetcher = PrLabelFetcher(self.manager)
        label = fetcher.get(self.number)
        if label is None:
            raise KeyError(f"Could not find name of PR #{self.number}!")
            return
        self.finished.emit(label)
