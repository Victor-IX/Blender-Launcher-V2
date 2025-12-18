from __future__ import annotations

import base64
import json
import logging
from itertools import chain
from typing import TYPE_CHECKING

import distro
from modules._platform import (
    get_architecture,
    get_platform,
)
from modules.bl_api_manager import (
    dropdown_blender_version,
    lts_blender_version,
    update_local_api_files,
    update_stable_builds_cache,
)
from modules.build_info import BuildInfo
from modules.scraper_cache import ScraperCache
from modules.settings import (
    get_scrape_bfa_builds,
    get_scrape_daily_builds,
    get_scrape_experimental_builds,
    get_scrape_stable_builds,
    get_show_daily_archive_builds,
    get_show_experimental_archive_builds,
    get_show_patch_archive_builds,
    get_use_pre_release_builds,
)
from PySide6.QtCore import QThread, Signal
from semver import Version

from source.threads.scraping.automated import ScraperAutomated
from source.threads.scraping.bfa import ScraperBfa
from source.threads.scraping.stable import ScraperStable

if TYPE_CHECKING:
    from modules.connection_manager import ConnectionManager

    from source.threads.scraping.base import BuildScraper

logger = logging.getLogger()


def get_release_tag(connection_manager: ConnectionManager) -> str | None:
    if get_use_pre_release_builds():
        url = "https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/releases"
        latest_tag = get_tag(connection_manager, url, pre_release=True)
    else:
        url = "https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest"
        latest_tag = get_tag(connection_manager, url)

    logger.info(f"Latest release tag: {latest_tag}")

    return latest_tag


def get_tag(
    connection_manager: ConnectionManager,
    url: str,
    pre_release=False,
) -> str | None:
    r = connection_manager.request("GET", url)

    if r is None:
        return None

    if pre_release:
        try:
            parsed_data = json.loads(r.data)
        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse pre-release tag JSON data: {e}")
            return None

        platform = get_platform()

        if platform.lower() == "linux":
            for key in (
                distro.id().title(),
                distro.like().title(),
                distro.id(),
                distro.like(),
            ):
                if "ubuntu" in key.lower():
                    platform = "Ubuntu"
                    break

        platform_valid_tags = (
            release["tag_name"]
            for release in parsed_data
            for asset in release["assets"]
            if asset["name"].endswith(".zip") and platform.lower() in asset["name"].lower()
        )
        pre_release_tags = (release.lstrip("v") for release in platform_valid_tags)

        valid_pre_release_tags = [tag for tag in pre_release_tags if Version.is_valid(tag)]

        if valid_pre_release_tags:
            tag = max(valid_pre_release_tags, key=Version.parse)
            return f"v{tag}"

        r.release_conn()
        r.close()

        return None

    else:
        url = r.geturl()
        tag = url.rsplit("/", 1)[-1]

        r.release_conn()
        r.close()

        return tag


def get_api_data(connection_manager: ConnectionManager, file: str) -> str | None:
    base_fmt = "https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/contents/source/resources/api/{}.json"
    url = base_fmt.format(file)
    logger.debug(f"Start fetching API data from: {url}")
    r = connection_manager.request("GET", url)

    if r is None:
        logger.error(f"Failed to fetch data from: {url}.")
        return None

    try:
        data = json.loads(r.data)
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to parse {file} API JSON data: {e}")
        return None

    file_content = data.get("content")
    file_content_encoding = data.get("encoding")

    if file_content_encoding == "base64" and file_content:
        try:
            file_content = base64.b64decode(file_content).decode("utf-8")
            json_data = json.loads(file_content)
            logger.info(f"API data form {file} have been loaded successfully")
            return json_data
        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.exception(f"Failed to decode or parse JSON data: {e}")
            return None
    else:
        logger.error(f"Failed to load API data from {file} or unsupported encoding.")
        return None


def get_latest_patch_note(connection_manager: ConnectionManager, latest_tag) -> str | None:
    if latest_tag is None:
        logger.error("Failed to get the latest release tag.")
        return None

    url = f"https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/releases/tags/{latest_tag}"
    r = connection_manager.request("GET", url)

    if r is None:
        logger.error(f"Failed to fetch release notes for tag: {latest_tag}")
        return None

    try:
        release_data = json.loads(r.data)
        patch_note = release_data.get("body", "No patch notes available.")
        logger.info("Latest patch note found")
        return patch_note
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to parse release notes JSON data: {e}")
        return None


class Scraper(QThread):
    links = Signal(BuildInfo)
    new_bl_version = Signal(str, str)
    error = Signal()
    stable_error = Signal(str)

    def __init__(self, parent, man: ConnectionManager, build_cache=False):
        QThread.__init__(self)
        self.parent = parent
        self.manager = man
        self.build_cache = build_cache

        self.platform = get_platform()
        self.architecture = get_architecture()

        self.scrape_stable = get_scrape_stable_builds()
        self.scrape_daily = get_scrape_daily_builds()
        self.scrape_experimental = get_scrape_experimental_builds()
        self.scrape_bfa = get_scrape_bfa_builds()

        self._latest_tag_cache = None

    def run(self):
        self.get_api_data_manager()
        self.get_download_links()
        self.get_new_release_manager()

    def get_cached_release_tag(self) -> str | None:
        if self._latest_tag_cache is None:
            self._latest_tag_cache = get_release_tag(self.manager)
        return self._latest_tag_cache

    def get_new_release_manager(self):
        assert self.manager.manager is not None
        latest_tag = self.get_cached_release_tag()

        if latest_tag is not None:
            patch_note = get_latest_patch_note(self.manager, latest_tag)
            self.new_bl_version.emit(latest_tag, patch_note)
        self.manager.manager.clear()

    def get_api_data_manager(self):
        assert self.manager.manager is not None

        bl_api_data = get_api_data(self.manager, "blender_launcher_api")
        blender_version_api_data = get_api_data(self.manager, f"stable_builds_api_{self.platform.lower()}")

        if bl_api_data is not None:
            update_local_api_files(bl_api_data)
            lts_blender_version()
            dropdown_blender_version()

        update_stable_builds_cache(blender_version_api_data)

        self.cache = ScraperCache.from_file_or_default(self.cache_path)
        self.manager.manager.clear()

    def scrapers(self):
        ss: list[BuildScraper] = []
        if self.scrape_stable:
            ss.append(ScraperStable(self.manager, self.stable_error, self.build_cache))
        if self.scrape_daily:
            ss.extend(self.scrape_daily_releases())
        if self.scrape_experimental:
            ss.extend(self.scrape_experimental_releases())
        if self.scrape_bfa:
            ss.append(ScraperBfa())
        return ss

    def get_download_links(self):
        ss = self.scrapers()

        for build in chain(*(s.scrape() for s in ss)):
            # Filter out builds that don't match the current platform for Windows
            if self.platform.lower() == "windows":
                if self.architecture == "arm64" and "arm64" in build.link:
                    self.links.emit(build)
                    continue
                elif self.architecture == "amd64" and (
                    ("x64" in build.link or "windows64" in build.link)
                    or "amd64" in build.link
                    or "bforartists" in build.link.lower()
                ):
                    self.links.emit(build)
                    continue
                else:
                    logger.debug(f"Skipping {build.link} as it doesn't match the current platform")
            else:
                self.links.emit(build)
                continue

    def scrape_daily_releases(self):
        b = "daily"
        if get_show_daily_archive_builds():
            b += "/archive"
        yield ScraperAutomated(self.manager, b)

    def scrape_experimental_releases(self):
        b = "experimental"
        if get_show_experimental_archive_builds():
            b += "/archive"
        yield ScraperAutomated(self.manager, b)
        b = "patch"
        if get_show_patch_archive_builds():
            b += "/archive"
        yield ScraperAutomated(self.manager, b)
