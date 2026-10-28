from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from modules.build_info import BuildInfo
from modules.platform_utils import bfa_cache_path, get_architecture, get_platform
from modules.scraper_cache import ScraperCache
from semver import Version
from threads.scraping.base import BuildScraper

if TYPE_CHECKING:
    from collections.abc import Generator

    from modules.connection_manager import ConnectionManager

logger = logging.getLogger()

BFA_DOWNLOADS_URL = "https://downloads.bforartists.com/"
BFA_DEVBUILDS_URL = "https://devbuilds.bforartists.com/"
_BFA_MACOS_ARM_KEYWORDS = ("silicon", "arm64")
_BFA_MACOS_INTEL_KEYWORDS = ("intel", "x86_64", "x64")


class ScraperBfa(BuildScraper):
    def __init__(self, man: ConnectionManager):
        self.manager = man
        self.cache_path = bfa_cache_path()
        self.cache = ScraperCache.from_file_or_default(self.cache_path)

    def scrape(self) -> Generator[BuildInfo, None, None]:
        # Only use cached timestamps for URLs still present in the new indexes.
        # This also discards obsolete Nextcloud links and expired developer builds.
        previous = {asset.link: asset for folder in self.cache.folders.values() for asset in folder.assets}
        fresh = ScraperCache()
        for url, developer in ((BFA_DOWNLOADS_URL, False), (BFA_DEVBUILDS_URL, True)):
            response = self.manager.request("GET", url)
            if response is None:
                continue
            try:
                if response.status != 200:
                    logger.warning("Failed to fetch Bforartists index %s: HTTP %s", url, response.status)
                    continue
                soup = BeautifulSoup(response.data, "lxml")
            finally:
                response.release_conn()
                response.close()

            seen = set()
            for section in soup.select("details"):
                summary = section.find("summary")
                if summary is None:
                    continue
                title = summary.get_text(" ", strip=True)
                try:
                    if developer:
                        match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", title)
                        if match is None:
                            continue
                        date = datetime.strptime(match[0], "%Y-%m-%d").replace(tzinfo=UTC)
                        # The index provides dates, not application version numbers.
                        version = Version(0, 0, int(date.strftime("%Y%m%d")), prerelease="dev")
                    else:
                        match = re.search(r"Bforartists\s+(\d+\.\d+\.\d+)\b", title, re.IGNORECASE)
                        if match is None:
                            continue
                        version = Version.parse(match[1])
                        date = None
                except ValueError:
                    logger.warning("Invalid Bforartists index heading: %s", title)
                    continue

                candidates = []
                for anchor in section.select("a[href]"):
                    link = urljoin(url, anchor["href"])
                    if urlparse(link).netloc != urlparse(url).netloc or urlparse(link).scheme != "https":
                        continue
                    filename = unquote(PurePosixPath(urlparse(link).path).name)
                    if link in seen or not self.matches_platform(filename):
                        continue
                    seen.add(link)
                    candidates.append((PurePosixPath(filename), link))
                if get_platform() == "macOS":
                    candidates = self.filter_macos_candidates(candidates)

                for _, link in candidates:
                    timestamp = date
                    if timestamp is None:
                        cached = previous.get(link)
                        timestamp = cached.commit_time if cached else self.release_timestamp(link)
                    if timestamp is None:
                        continue
                    build = BuildInfo(
                        link,
                        str(version),
                        None,
                        timestamp,
                        "bforartists",
                        custom_executable={"Windows": "bforartists.exe", "Linux": "bforartists"}.get(get_platform()),
                    )
                    if version not in fresh:
                        fresh.new_build(version, timestamp)
                    fresh[version].assets.append(build)
                    yield build

        self.cache = fresh
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("w", encoding="utf-8") as file:
                json.dump(self.cache.to_dict(), file)
        except OSError:
            logger.exception("Failed to write Bforartists cache")

    def release_timestamp(self, url: str) -> datetime | None:
        response = self.manager.request("HEAD", url)
        if response is None:
            return None
        try:
            if response.status != 200:
                return None
            timestamp = parsedate_to_datetime(response.headers.get("Last-Modified", ""))
            return timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp
        except (TypeError, ValueError):
            logger.warning("Missing or invalid Last-Modified for %s", url)
            return None
        finally:
            response.release_conn()
            response.close()

    @staticmethod
    def matches_platform(filename: str) -> bool:
        name = filename.lower()
        if get_platform() == "Windows":
            return name.endswith(".zip") and (
                "windows" in name or "win64" in name or re.fullmatch(r"bforartists[23]_\d+\.zip", name) is not None
            )
        if get_platform() == "macOS":
            return name.endswith(".dmg")
        return "linux" in name and name.endswith((".tar.xz", ".tar.gz"))

    @staticmethod
    def filter_macos_candidates(candidates):
        """Prefer the native DMG, then a universal or unlabelled package."""
        is_arm = get_architecture() == "arm64"
        own = _BFA_MACOS_ARM_KEYWORDS if is_arm else _BFA_MACOS_INTEL_KEYWORDS
        other = _BFA_MACOS_INTEL_KEYWORDS if is_arm else _BFA_MACOS_ARM_KEYWORDS
        filtered = [c for c in candidates if not any(kw in c[0].name.lower() for kw in other)]
        native = [c for c in filtered if any(kw in c[0].name.lower() for kw in own)]
        return native[:1] if native else filtered[:1]
