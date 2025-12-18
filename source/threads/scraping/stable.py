from __future__ import annotations

import contextlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import dateparser
from bs4 import BeautifulSoup, SoupStrainer
from modules._platform import (
    get_architecture,
    get_platform,
    stable_cache_path,
)
from modules.build_info import BuildInfo, parse_blender_ver
from modules.scraper_cache import ScraperCache
from modules.settings import (
    get_minimum_blender_stable_version,
)
from semver import Version

from source.threads.scraping.base import BuildScraper, regex_filter

if TYPE_CHECKING:
    from collections.abc import Generator

    from modules.connection_manager import ConnectionManager
    from PySide6.QtCore import SignalInstance

logger = logging.getLogger()


HASH_RE = re.compile(r"\w{12}")
BLENDER_X_X = re.compile(r"Blender(\d+\.\d+)")


class ScraperStable(BuildScraper):
    def __init__(self, man: ConnectionManager, stable_error: SignalInstance, force_build_cache: bool = False):
        super().__init__()
        self.manager = man
        self.stable_error = stable_error
        self.force_build_cache: bool = force_build_cache

        self.cache_path = stable_cache_path()
        self.cache = ScraperCache.from_file_or_default(self.cache_path)
        self.architecture = get_architecture()

    def refresh_cache(self):
        self.cache = ScraperCache.from_file_or_default(self.cache_path)

    def scrape(self) -> Generator[BuildInfo, None, None]:
        if not self.force_build_cache:
            yield from self.scrape_stable_releases()
            return

        for platform in ["Windows", "linux", "macOS"]:
            yield from self.scrape_stable_releases(platform)

    def scrape_stable_releases(self, platform=None):
        # Use for cache building only
        if self.force_build_cache and platform is not None:
            self.platform = platform
            self.cache_path = stable_cache_path().with_name(f"stable_builds_{platform}.json")
            self.cache = ScraperCache.from_file_or_default(self.cache_path)
            logging.debug(f"Scraping stable releases for {platform}")

        link_filter = regex_filter(platform)

        url = "https://download.blender.org/release/"
        r = self.manager.request("GET", url)

        if r is None:
            return

        content = r.data
        soup = BeautifulSoup(content, "lxml")

        releases = soup.find_all(href=BLENDER_X_X)
        if not any(releases):
            logger.info(f"Failed to gather stable releases for {platform}")
            logger.info(content)
            self.stable_error.emit(
                f"No releases were scraped from the site for {platform}!<br>check -debug logs for more details."
            )
            return

        minimum_version_str = get_minimum_blender_stable_version()
        if minimum_version_str == "None":
            minimum_smver_version = Version(2, 48, 0)
        else:
            major, minor = minimum_version_str.split(".")
            minimum_smver_version = Version(int(major), int(minor), 0)

        if self.force_build_cache:
            minimum_smver_version = Version(2, 48, 0)

        cache_modified = False
        for release in releases:
            href = release["href"]
            match = re.search(BLENDER_X_X, href)
            if match is None:
                continue

            ver = parse_blender_ver(match.group(1))
            if ver >= minimum_smver_version:
                # Check modified dates of folders, if available
                date_sibling = release.find_next_sibling(string=True)
                if date_sibling:
                    date_str = " ".join(date_sibling.strip().split()[:2])
                    with contextlib.suppress(ValueError):
                        modified_date = dateparser.parse(date_str)
                        if ver not in self.cache:
                            logger.debug(f"Creating new folder for version {ver}")
                            folder = self.cache.new_build(ver)
                        else:
                            folder = self.cache[ver]

                        if folder.modified_date != modified_date:
                            folder.assets.clear()
                            for build in self.scrap_download_links(urljoin(url, href), link_filter):
                                folder.assets.append(build)
                                yield build

                            logger.debug(
                                f"Caching {href}: {modified_date} (previous was {folder.modified_date}) for platform {platform}"
                            )
                            folder.modified_date = modified_date
                            cache_modified = True
                        else:
                            logger.debug(f"Skipping {href}: {modified_date} for platform {platform}")

                        builds = self.cache[ver].assets

                        if not self.force_build_cache:
                            yield from builds
                        continue

                yield from self.scrap_download_links(urljoin(url, href), link_filter)

        if cache_modified:
            cache_path = self.cache_path
            new_file_ver = "0.1"
            # Get Local API file instead of the generated one
            # TODO: Make a function to get app file path if not already done
            if self.force_build_cache:
                cache_path = (
                    Path(sys._MEIPASS) / f"files/stable_builds_api_{get_platform().lower()}.json"
                    if getattr(sys, "frozen", False)
                    else Path(f"source/resources/api/stable_builds_api_{get_platform().lower()}.json").resolve()
                )
                new_file_ver = "1.0"

            try:
                with open(cache_path) as f:
                    current_data = json.load(f)
                    file_ver = current_data.get("api_file_version", "0.0")
                    major, minor = map(int, file_ver.split("."))
                    if self.force_build_cache:
                        major += 1
                    else:
                        minor += 1
                    new_file_ver = f"{major}.{minor}"
                    logger.debug(f"Updating cache file version to {new_file_ver}")
            except json.JSONDecodeError:
                logger.exception("Failed to read api_file_version file. Using default 0.1")
            except ValueError:
                logger.exception("Invalid api_file_version version format. Using default 0.1")
            except Exception as e:
                logger.exception(f"Failed to read api_file_version version, using default 0.1: {e}")

            cache_path = self.cache_path
            cache_data = self.cache.to_dict()
            cache_data = {"api_file_version": new_file_ver, **cache_data}

            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=1)
                logging.info(f"Saved updated cache to {cache_path}")

        r.release_conn()
        r.close()

    def scrap_download_links(self, url, link_filter: re.Pattern, _limit=None):
        r = self.manager.request("GET", url)

        if r is None:
            return

        content = r.data

        soup_stainer = SoupStrainer("a", href=True)
        soup = BeautifulSoup(content, "lxml", parse_only=soup_stainer)

        for tag in soup.find_all(limit=_limit, href=link_filter):
            build_info = self.new_blender_build(tag, url, content)

            if build_info is not None:
                yield build_info

        r.release_conn()
        r.close()

    def new_blender_build(self, tag, url, content):
        link = urljoin(url, tag["href"]).rstrip("/")

        # Get commit time from content instead of creating a new request for each build
        pattern = re.compile(r'href="[^"]*' + re.escape(tag["href"]) + r'"')

        for line in content.decode("utf-8").splitlines():
            if pattern.search(line):
                time_pattern = r"(\d{1,2}-\w{3}-\d{4})\s+(\d{2}:\d{2})"
                match = re.search(time_pattern, line)
                if match:
                    date = match.group(1)
                    time = match.group(2)
                    datetime_str = f"{date} {time} GMT"
                    commit_time = dateparser.parse(datetime_str).astimezone()

        build_hash: str | None = None
        stem = Path(link).stem
        match = re.findall(HASH_RE, stem)

        if match:
            build_hash = match[-1].replace("-", "")

        subversion = parse_blender_ver(stem, search=True)

        if self.platform == "macOS":
            # Skip Intel builds on Apple Silicon
            if self.architecture == "arm64" and "arm64" not in link:
                return None

            # Skip Apple Silicon builds on Intel
            if self.architecture == "x64" and "x64" not in link:
                return None

        return BuildInfo(link, str(subversion), build_hash, commit_time, "stable")
