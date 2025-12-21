from __future__ import annotations

import logging
from itertools import chain
from typing import TYPE_CHECKING

from modules._platform import (
    get_architecture,
    get_platform,
)
from modules.build_info import BuildInfo
from modules.settings import (
    get_scrape_bfa_builds,
    get_scrape_daily_builds,
    get_scrape_experimental_builds,
    get_scrape_stable_builds,
    get_show_daily_archive_builds,
    get_show_experimental_archive_builds,
    get_show_patch_archive_builds,
)
from PySide6.QtCore import QThread, Signal
from threads.scraping.automated import ScraperAutomated
from threads.scraping.bfa import ScraperBfa
from threads.scraping.launcher_updates import LauncherDataUpdater
from threads.scraping.stable import ScraperStable

if TYPE_CHECKING:
    from modules.connection_manager import ConnectionManager
    from threads.scraping.base import BuildScraper

logger = logging.getLogger()


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

        # these are saved because they hold caches
        self.scraper_stable = ScraperStable(self.manager, self.stable_error, self.build_cache)
        self.scraper_bfa = ScraperBfa()

        self.launcher_data_updater = LauncherDataUpdater(self.manager)

        self._latest_tag_cache = None

    def run(self):
        self.launcher_data_updater.get_api_data_updates()
        self.scraper_stable.refresh_cache()

        self.get_download_links()

        rel = self.launcher_data_updater.check_for_new_releases()
        if rel is not None:
            self.new_bl_version.emit(*rel)

    def scrapers(self):
        scrapers: list[BuildScraper] = []
        if self.scrape_stable:
            scrapers.append(self.scraper_stable)
        if self.scrape_daily:
            scrapers.extend(self.scrape_daily_releases())
        if self.scrape_experimental:
            scrapers.extend(self.scrape_experimental_releases())
        if self.scrape_bfa:
            scrapers.append(self.scraper_bfa)
        return scrapers

    def get_download_links(self):
        ss = self.scrapers()

        for build in chain(*(s.scrape() for s in ss)):
            # Filter out builds that don't match the current platform for Windows
            if self.platform.lower() == "windows":
                if self.architecture == "arm64" and "arm64" in build.link:
                    self.links.emit(build)
                    continue
                if self.architecture == "amd64" and (
                    ("x64" in build.link or "windows64" in build.link)
                    or "amd64" in build.link
                    or "bforartists" in build.link.lower()
                ):
                    self.links.emit(build)
                    continue

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
