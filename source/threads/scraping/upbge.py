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

UPBGE_GITHUB_API_URL = "https://api.github.com/repos/UPBGE/upbge/releases?per_page=100"
UPBGE_MINIMUM_VERSION = Version(0, 30, 0)  # Skip releases before 0.30

plat = get_platform()
if plat == "Windows":
    upbge_regex_filter = r"upbge-.+windows.+\.(zip|7z)$"
elif plat == "macOS":
    upbge_regex_filter = r"upbge-.+macos.+\.(zip|dmg)$"
else:
    upbge_regex_filter = r"upbge-.+linux.+\.(tar\.xz|tar\.gz)$"

upbge_package_file_name_regex = re.compile(upbge_regex_filter, re.IGNORECASE)


class ScraperUpbge(BuildScraper):
    def __init__(self, man: ConnectionManager, scrape_weekly_builds: bool = True):
        super().__init__()
        self.manager = man
        self.scrape_weekly_builds = scrape_weekly_builds

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

        # Check if response is an error (rate limit or other GitHub API error)
        if isinstance(releases, dict):
            if "message" in releases:
                error_msg = releases.get("message", "Unknown error")

                # Check for rate limit specifically
                if "rate limit" in error_msg.lower():
                    logger.warning("GitHub API rate limit exceeded. UPBGE builds will not be available.")
                else:
                    logger.error(f"GitHub API error for UPBGE: {error_msg}")
                return

            # If it's a dict but not an error, it's an unexpected response
            logger.error(f"Unexpected response format from GitHub API: {type(releases)}")
            return

        # Validate that releases is a list
        if not isinstance(releases, list):
            logger.error(f"Expected list of releases, got {type(releases)}")
            return

        for release in releases:
            if not isinstance(release, dict):
                logger.warning(f"Skipping invalid release entry: {type(release)}")
                continue

            if release.get("draft", False):
                continue

            tag_name = release.get("tag_name", "")
            release_date = release.get("published_at")

            if not tag_name or not release_date:
                continue

            is_weekly = tag_name.startswith("weekly-build-")

            # Check version for non-weekly releases (e.g., v0.25, v0.30)
            if not is_weekly:
                try:
                    version_str = tag_name.lstrip("v")
                    version = parse_blender_ver(version_str)
                    if version < UPBGE_MINIMUM_VERSION:
                        logger.debug(f"Skipping old UPBGE release: {tag_name} (< {UPBGE_MINIMUM_VERSION})")
                        continue
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse version for {tag_name}, including it: {e}")

            # Check for weekly builds if disabled
            if is_weekly and not self.scrape_weekly_builds:
                # Check assets to see if any contain alpha
                assets = release.get("assets", [])
                has_alpha = any("-alpha" in asset.get("name", "").lower() for asset in assets)
                if has_alpha:
                    logger.debug(f"Skipping UPBGE weekly release: {tag_name}")
                    continue

            try:
                commit_time = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse UPBGE release date {release_date}: {e}")
                continue

            # Get commit hash from tag
            build_hash = None
            try:
                tag_url = f"https://api.github.com/repos/UPBGE/upbge/git/refs/tags/{tag_name}"
                tag_response = self.manager.request("GET", tag_url)
                if tag_response:
                    tag_data = json.loads(tag_response.data)

                    # Check if response is an error (rate limit)
                    if isinstance(tag_data, dict) and "message" in tag_data:
                        logger.debug(f"Could not fetch hash for {tag_name}: {tag_data.get('message')}")
                    else:
                        commit_sha = tag_data.get("object", {}).get("sha")
                        if commit_sha:
                            # Use first 12 characters of commit SHA (standard short hash)
                            build_hash = commit_sha[:12]
                            logger.debug(f"UPBGE {tag_name} commit hash: {build_hash}")
            except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as e:
                logger.debug(f"Failed to get commit hash for UPBGE {tag_name}: {e}")

            assets = release.get("assets", [])
            for asset in assets:
                asset_name = asset.get("name", "")
                download_url = asset.get("browser_download_url")

                if not download_url or not upbge_package_file_name_regex.match(asset_name):
                    continue

                try:
                    # Determine if this is a weekly or stable build
                    is_weekly = tag_name.startswith("weekly-build-")
                    is_alpha = "-alpha" in asset_name.lower()

                    if is_weekly:
                        # Check if we should scrape alpha builds
                        if is_alpha and not self.scrape_weekly_builds:
                            continue

                        # Extract version from asset filename (e.g., "upbge-0.51-alpha-windows...")
                        version_match = re.search(r"upbge-([0-9.]+(?:-alpha)?)-", asset_name, re.IGNORECASE)
                        if version_match:
                            version_str = version_match.group(1)
                            subversion = parse_blender_ver(version_str)
                        else:
                            # Fallback to build number if version not found in filename
                            build_num = tag_name.replace("weekly-build-", "")
                            subversion = Version(0, 0, int(build_num), prerelease="weekly")
                        branch = "upbge-weekly" if is_alpha else "upbge-stable"
                    else:
                        # Stable release - parse version from tag
                        version_str = tag_name.lstrip("v")
                        subversion = parse_blender_ver(version_str)
                        branch = "upbge-stable"
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
                    build_hash,
                    commit_time,
                    branch,
                    custom_executable=exe_name,
                )
