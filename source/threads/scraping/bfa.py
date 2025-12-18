from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin

from modules._platform import (
    bfa_cache_path,
    get_platform,
)
from modules.build_info import BuildInfo
from modules.scraper_cache import ScraperCache
from semver import Version
from threads.scraping.base import BuildScraper
from webdav4.client import Client

logger = logging.getLogger()

# NC: NextCloud
BFA_NC_BASE_URL = "https://cloud.bforartists.de"
BFA_NC_HTTPS_URL = f"{BFA_NC_BASE_URL}/index.php/s"
# https://archive.ph/esTuX#accessing-public-shares-over-webdav
BFA_NC_WEBDAV_URL = f"{BFA_NC_BASE_URL}/public.php/webdav"
BFA_NC_WEBDAV_SHARE_TOKEN = "JxCjbyt2fFcHjy4"


def get_bfa_nc_https_download_url(webdav_file_path: PurePosixPath):
    return f"{BFA_NC_WEBDAV_URL}/{webdav_file_path}"


plat = get_platform()
if plat == "Windows":
    bfa_regex_filter = r"Bforartists-.+Windows.+zip"
elif plat == "macOS":
    bfa_regex_filter = r"Bforartists-.+dmg$"
else:
    bfa_regex_filter = r"Bforartists-.+tar.xz$"

bfa_package_file_name_regex = re.compile(bfa_regex_filter, re.IGNORECASE)


class ScraperBfa(BuildScraper):
    def __init__(self):
        super().__init__()

        self.cache_path = bfa_cache_path()
        self.cache = ScraperCache.from_file_or_default(self.cache_path)

    def scrape(self) -> Generator[BuildInfo, None, None]:
        client = Client(BFA_NC_WEBDAV_URL, auth=(BFA_NC_WEBDAV_SHARE_TOKEN, ""))
        cache_modified = False
        for entry in client.ls("", detail=True, allow_listing_resource=True):
            if isinstance(entry, str):
                continue
            if entry["type"] != "directory":
                continue
            try:
                semver = Version.parse(entry["name"].split()[-1])
            except ValueError:
                continue

            # check if the cache needs to be updated
            modified_date: datetime = entry["modified"]
            if semver not in self.cache:
                folder = self.cache.new_build(semver)
            else:
                folder = self.cache[semver]

            if folder.modified_date < modified_date:
                # Clear existing assets and replace with fresh data
                folder.assets.clear()
                for release in self.scrape_bfa_release(client, entry["name"], semver):
                    folder.assets.append(release)
                    yield release

                folder.modified_date = modified_date
                cache_modified = True
            else:
                logger.debug(f"Skipping {entry['name']}: {modified_date}")
                yield from folder.assets

        if cache_modified:
            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump(self.cache.to_dict(), f)
                logging.debug(f"Saved cache to {self.cache_path}")

    def scrape_bfa_release(self, client: Client, folder: str, semver: Version):
        for entry in client.ls(folder, detail=True, allow_listing_resource=True):
            if isinstance(entry, str):
                continue
            path = entry["name"]
            ppath = PurePosixPath(path)
            if bfa_package_file_name_regex.match(ppath.name) is None:
                continue
            commit_time = entry["modified"]
            if not isinstance(commit_time, datetime):
                continue

            # Set custom_executable for Windows/Linux since Bforartists uses a different
            # executable name than Blender. On macOS, let it be auto-detected during
            # installation to handle DMG-extracted .app bundles correctly.
            platform = get_platform()
            if platform == "macOS":
                exe_name = None
            else:
                exe_name = {
                    "Windows": "bforartists.exe",
                    "Linux": "bforartists",
                }.get(platform, "bforartists")

            # Don't set custom_executable - let it be auto-detected during installation
            # This ensures consistent behavior with Blender
            yield BuildInfo(
                get_bfa_nc_https_download_url(ppath),
                str(semver),
                None,
                commit_time.astimezone(),
                "bforartists",
                custom_executable=exe_name,
            )
