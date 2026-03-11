import json
import logging
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from modules.connection_manager import ConnectionManager
from modules.platform_utils import labels_cache_path

logger = logging.getLogger()


PAGE_SIZE = 50
PULLS_LINK = f"https://projects.blender.org/api/v1/repos/blender/blender/pulls?limit={PAGE_SIZE}&sort=recentupdate"
INDIVIDUAL_PULLS = "https://projects.blender.org/api/v1/repos/blender/blender/pulls/{}"
MAX_PAGE_REQUESTS = 4


class Pr(TypedDict):  # Only relevant fields
    number: int
    title: str
    # ...


class PrLabelFetcher:
    def __init__(self, man: ConnectionManager):
        self.manager = man

        self.path = labels_cache_path()

        self._label_cache: LabelCache = LabelCache.try_from_file(self.path) or LabelCache({})

    def fetch_one(self, pr: int) -> Pr | None:
        r = self.manager.request("GET", INDIVIDUAL_PULLS.format(pr))
        if r is None:
            logger.error("Failed to fetch PR ", pr)
            return None
        return json.loads(r.data)

    def fetch(self, page: int | None = None) -> list[Pr] | None:
        if page is not None:
            url = PULLS_LINK + f"&page={page}"
        else:
            url = PULLS_LINK

        # url += "&state=open"

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
            if len(self._label_cache.found.keys() - labels.keys()) == 0:
                break

            self._label_cache.found.update(labels)

    def get_cached(self, x: int) -> str | None:
        return self._label_cache.found.get(x)

    def get(self, x: int) -> str | None:
        # check if we already know it
        if x in self._label_cache.found:
            return self._label_cache.found[x]

        logger.debug("PR %s missing, searching...", x)

        pr = self.fetch_one(x)
        if pr is not None:
            self.__add_to_cache(x, pr["title"].strip())
            return self._label_cache.found[x]
        return None

    def __add_to_cache(self, x: int, v: str):
        self._label_cache.largest = max(self._label_cache.largest, x)
        self._label_cache.found[x] = v

    def save(self):
        self._label_cache.write(self.path)


def _pr_labels(lst: list[Pr]) -> dict[int, str]:
    return {pr["number"]: pr["title"].strip() for pr in lst}


@dataclass
class LabelCache:
    found: dict[int, str]
    largest: int = 0

    @classmethod
    def try_from_file(cls, file: Path):
        if not file.exists():
            logger.info(f"Cache file {file} does not exist, creating new cache")
            return None

        try:
            d = {}
            largest = 0
            with file.open("r", encoding="utf-8") as f:
                for line in f:
                    n, label = line.strip().split(":", 1)
                    d[int(n)] = label
                    largest = max(largest, int(n))
            logger.debug(f"Loaded cache from {file}")
            return cls(d, largest=largest)
        except (json.decoder.JSONDecodeError, OSError) as e:
            logger.exception(f"Failed to load cache {file}: {e}")
            return None

    def write(self, file: Path):
        with file.open("w", encoding="utf-8") as f:
            for n, label in sorted(self.found.items()):
                f.write(f"{n}:{label.strip()}\n")
