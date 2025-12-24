from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from modules._platform import get_platform
from modules.build_info import BuildInfo, parse_blender_ver
from semver import Version
from threads.scraping.base import BuildScraper

if TYPE_CHECKING:
    from collections.abc import Generator

    from modules.connection_manager import ConnectionManager

logger = logging.getLogger()

UPBGE_GITHUB_API_URL = "https://api.github.com/repos/UPBGE/upbge/releases"

plat = get_platform()
if plat == "Windows":
    upbge_regex_filter = r"upbge-.+windows.+\.zip$"
elif plat == "macOS":
    upbge_regex_filter = r"upbge-.+macos.+\.zip$"
else:
    upbge_regex_filter = r"upbge-.+linux.+\.tar\.xz$"

upbge_package_file_name_regex = re.compile(upbge_regex_filter, re.IGNORECASE)


class ScraperUpbge(BuildScraper):
    def __init__(self, man: ConnectionManager):
        super().__init__()
        self.manager = man

    def scrape(self) -> Generator[BuildInfo, None, None]:
        r = self.manager.request("GET", UPBGE_GITHUB_API_URL)

        if r is None:
            logger.error("Failed to fetch UPBGE releases from GitHub API")
            return

        try:
            releases = json.loads(r.data)
        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse UPBGE releases JSON: {e}")
            return

        for release in releases:
            if release.get("draft", False):
                continue

            tag_name = release.get("tag_name", "")
            release_date = release.get("published_at")

            if not tag_name or not release_date:
                continue

            try:
                commit_time = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse UPBGE release date {release_date}: {e}")
                continue

            assets = release.get("assets", [])
            for asset in assets:
                asset_name = asset.get("name", "")
                download_url = asset.get("browser_download_url")

                if not download_url or not upbge_package_file_name_regex.match(asset_name):
                    continue

                try:
                    version_str = tag_name.lstrip("v")
                    # Handle UPBGE's weekly-build-XX format
                    if version_str.startswith("weekly-build-"):
                        build_num = version_str.replace("weekly-build-", "")
                        # Create a version like 0.0.XX-weekly where XX is the build number
                        subversion = Version(0, 0, int(build_num), prerelease="weekly")
                    else:
                        subversion = parse_blender_ver(version_str)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse UPBGE version {tag_name}: {e}")
                    continue

                platform = get_platform()
                if platform == "macOS":
                    exe_name = None
                else:
                    exe_name = {
                        "Windows": "upbge.exe",
                        "Linux": "upbge",
                    }.get(platform, "upbge")

                yield BuildInfo(
                    download_url,
                    str(subversion),
                    None,
                    commit_time,
                    "upbge",
                    custom_executable=exe_name,
                )
