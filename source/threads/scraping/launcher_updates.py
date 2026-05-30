from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import TYPE_CHECKING

import distro
from modules.bl_api_manager import (
    dropdown_blender_version,
    lts_blender_version,
    update_local_api_files,
    update_stable_builds_cache,
)
from modules.platform_utils import get_platform
from modules.settings import get_use_pre_release_builds
from semver import Version

if TYPE_CHECKING:
    from modules.connection_manager import ConnectionManager


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
        redirect_url = r.geturl()

        r.release_conn()
        r.close()

        if redirect_url is None:
            return None

        return redirect_url.rsplit("/", 1)[-1]


def get_api_data(connection_manager: ConnectionManager, file: str) -> dict | None:
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
        except (binascii.Error, json.JSONDecodeError) as e:
            logger.exception(f"Failed to decode or parse JSON data: {e}")
            return None
    else:
        logger.error(f"Failed to load API data from {file} or unsupported encoding.")
        return None


def get_patch_notes_since_version(
    connection_manager: ConnectionManager,
    current_version: Version,
    latest_tag: str,
    include_pre_releases: bool = False,
) -> list[tuple[str, str]] | None:
    """Fetch patch notes for all releases between current_version (exclusive) and latest_tag (inclusive).

    Returns a list of (tag_name, body) tuples sorted newest-first, or None if no relevant releases.
    """
    url = "https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/releases?per_page=100"
    r = connection_manager.request("GET", url)

    if r is None:
        logger.error("Failed to fetch releases list.")
        return None

    try:
        releases_data = json.loads(r.data)
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to parse releases JSON data: {e}")
        return None

    latest_version = Version.parse(latest_tag.lstrip("v"))

    relevant_releases: list[tuple[Version, str, str]] = []
    for release in releases_data:
        tag = release.get("tag_name", "").lstrip("v")
        if not Version.is_valid(tag):
            continue
        ver = Version.parse(tag)
        if release.get("prerelease", False) and not include_pre_releases:
            continue
        if current_version < ver <= latest_version:
            body = release.get("body") or ""
            relevant_releases.append((ver, release.get("tag_name", f"v{tag}"), body))

    if not relevant_releases:
        return None

    # Sort newest first so the most recent changes appear at the top
    relevant_releases.sort(key=lambda x: x[0], reverse=True)

    return [(tag, body) for _ver, tag, body in relevant_releases]


class LauncherDataUpdater:
    def __init__(self, man: ConnectionManager):
        self.manager = man

        self.platform = get_platform()
        self._latest_tag_cache = None

    def get_api_data_updates(self):
        assert self.manager.manager is not None

        bl_api_data = get_api_data(self.manager, "blender_launcher_api")
        blender_version_api_data = get_api_data(self.manager, f"stable_builds_api_{self.platform.lower()}")

        if bl_api_data is not None:
            update_local_api_files(bl_api_data)
            lts_blender_version()
            dropdown_blender_version()

        update_stable_builds_cache(blender_version_api_data)
        self.manager.manager.clear()

    @property
    def latest_tag_cache(self):
        if self._latest_tag_cache is None:
            self._latest_tag_cache = get_release_tag(self.manager)
        return self._latest_tag_cache

    def check_for_new_releases(self, current_version: Version) -> tuple[str, list[tuple[str, str]] | None] | None:
        assert self.manager.manager is not None
        latest_tag = self.latest_tag_cache

        if latest_tag is not None:
            patch_notes = get_patch_notes_since_version(
                self.manager,
                current_version,
                latest_tag,
                include_pre_releases=get_use_pre_release_builds(),
            )
            logger.info(f"Patch notes collected for versions since {current_version} up to {latest_tag}")

            self.manager.manager.clear()

            return latest_tag, patch_notes
        self.manager.manager.clear()
        return None
