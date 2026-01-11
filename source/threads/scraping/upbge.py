from __future__ import annotations

import json
import logging
import re
from abc import abstractmethod
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


class ScraperUpbgeBase(BuildScraper):
    """Base class for UPBGE scrapers with common scraping logic."""

    def __init__(self, man: ConnectionManager):
        super().__init__()
        self.manager = man

    @abstractmethod
    def should_process_release(self, release: dict, tag_name: str, is_weekly: bool) -> bool:
        """Determine if a release should be processed by this scraper."""
        pass

    @abstractmethod
    def get_branch_name(self, is_weekly: bool, is_alpha: bool) -> str:
        """Get the branch name for the build."""
        pass

    def _fetch_releases(self) -> list[dict] | None:
        """Fetch releases from GitHub API."""
        r = self.manager.request("GET", UPBGE_GITHUB_API_URL)

        if r is None:
            logger.error("Failed to fetch UPBGE releases from GitHub API")
            return None

        try:
            releases = json.loads(r.data)
        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse UPBGE releases JSON: {e}")
            return None

        if isinstance(releases, dict):
            if "message" in releases:
                error_msg = releases.get("message", "Unknown error")
                if "rate limit" in error_msg.lower():
                    logger.warning("GitHub API rate limit exceeded. UPBGE builds will not be available.")
                else:
                    logger.error(f"GitHub API error for UPBGE: {error_msg}")
                return None
            logger.error(f"Unexpected response format from GitHub API: {type(releases)}")
            return None

        if not isinstance(releases, list):
            logger.error(f"Expected list of releases, got {type(releases)}")
            return None

        return releases

    def _get_commit_hash(self, tag_name: str) -> str | None:
        """Fetch commit hash for a given tag."""
        try:
            tag_url = f"https://api.github.com/repos/UPBGE/upbge/git/refs/tags/{tag_name}"
            tag_response = self.manager.request("GET", tag_url)
            if tag_response:
                tag_data = json.loads(tag_response.data)

                if isinstance(tag_data, dict) and "message" in tag_data:
                    logger.debug(f"Could not fetch hash for {tag_name}: {tag_data.get('message')}")
                else:
                    commit_sha = tag_data.get("object", {}).get("sha")
                    if commit_sha:
                        return commit_sha[:12]
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Failed to get commit hash for UPBGE {tag_name}: {e}")
        return None

    def _parse_version(self, tag_name: str, asset_name: str, is_weekly: bool) -> Version | None:
        """Parse version from tag or asset name."""
        try:
            if is_weekly:
                version_match = re.search(r"upbge-([0-9.]+(?:-alpha)?)-", asset_name, re.IGNORECASE)
                if version_match:
                    version_str = version_match.group(1)
                    return parse_blender_ver(version_str)
                else:
                    build_num = tag_name.replace("weekly-build-", "")
                    return Version(0, 0, int(build_num), prerelease="weekly")
            else:
                version_str = tag_name.lstrip("v")
                return parse_blender_ver(version_str)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse UPBGE version {tag_name}: {e}")
            return None

    def scrape(self) -> Generator[BuildInfo, None, None]:
        releases = self._fetch_releases()
        if releases is None:
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

            # Let child classes decide if this release should be processed
            if not self.should_process_release(release, tag_name, is_weekly):
                continue

            # Check version for non-weekly stable releases
            if not is_weekly:
                try:
                    version_str = tag_name.lstrip("v")
                    version = parse_blender_ver(version_str)
                    if version < UPBGE_MINIMUM_VERSION:
                        logger.debug(f"Skipping old UPBGE release: {tag_name} (< {UPBGE_MINIMUM_VERSION})")
                        continue
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse version for {tag_name}, including it: {e}")

            try:
                commit_time = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse UPBGE release date {release_date}: {e}")
                continue

            build_hash = self._get_commit_hash(tag_name)
            if build_hash:
                logger.debug(f"UPBGE {tag_name} commit hash: {build_hash}")

            assets = release.get("assets", [])
            for asset in assets:
                asset_name = asset.get("name", "")
                download_url = asset.get("browser_download_url")

                if not download_url or not upbge_package_file_name_regex.match(asset_name):
                    continue

                is_alpha = "-alpha" in asset_name.lower()
                subversion = self._parse_version(tag_name, asset_name, is_weekly)
                if subversion is None:
                    continue

                branch = self.get_branch_name(is_weekly, is_alpha)

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


class ScraperUpbgeStable(ScraperUpbgeBase):
    """Scraper for UPBGE stable releases only."""

    def should_process_release(self, release: dict, tag_name: str, is_weekly: bool) -> bool:
        """Only process stable releases (non-weekly)."""
        if is_weekly:
            return False

        # Check assets to exclude any that contain alpha
        assets = release.get("assets", [])
        has_alpha = any("-alpha" in asset.get("name", "").lower() for asset in assets)
        if has_alpha:
            logger.debug(f"Skipping UPBGE alpha release in stable scraper: {tag_name}")
            return False

        return True

    def get_branch_name(self, is_weekly: bool, is_alpha: bool) -> str:
        """Stable releases always use upbge-stable branch."""
        return "upbge-stable"


class ScraperUpbgeWeekly(ScraperUpbgeBase):
    """Scraper for UPBGE weekly/alpha builds."""

    def should_process_release(self, release: dict, tag_name: str, is_weekly: bool) -> bool:
        """Only process weekly releases."""
        if not is_weekly:
            return False

        # Check assets to ensure at least one contains alpha
        assets = release.get("assets", [])
        has_alpha = any("-alpha" in asset.get("name", "").lower() for asset in assets)
        if not has_alpha:
            logger.debug(f"Skipping UPBGE weekly release without alpha builds: {tag_name}")
            return False

        return True

    def get_branch_name(self, is_weekly: bool, is_alpha: bool) -> str:
        """Weekly releases use upbge-weekly branch."""
        return "upbge-weekly"
