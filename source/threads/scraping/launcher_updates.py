from __future__ import annotations

import base64
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
        url = r.geturl()
        tag = url.rsplit("/", 1)[-1]

        r.release_conn()
        r.close()

        return tag


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

    def check_for_new_releases(self) -> tuple[str, str | None] | None:
        assert self.manager.manager is not None
        latest_tag = self.latest_tag_cache

        if latest_tag is not None:
            patch_note = get_latest_patch_note(self.manager, latest_tag)

            self.manager.manager.clear()

            return latest_tag, patch_note
        self.manager.manager.clear()
        return None
