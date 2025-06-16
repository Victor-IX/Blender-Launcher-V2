from __future__ import annotations

import logging

from semver import Version
from typing import TYPE_CHECKING, List, Any, Optional

from modules.settings import (
    get_use_advanced_update_button,
    get_update_behavior,
    get_stable_update_behavior,
    get_daily_update_behavior,
    get_experimental_update_behavior,
    get_bfa_update_behavior,
    get_show_update_button,
    get_show_stable_update_button,
    get_show_daily_update_button,
    get_show_experimental_update_button,
    get_show_bfa_update_button,
)

if TYPE_CHECKING:
    from modules.build_info import BuildInfo

logger = logging.getLogger()


def available_blender_update(
    current_build_info: BuildInfo,
    available_downloads: List[Any],
    widgets: Any,
):
    """
    Check available update only for branches matching the settings.
    """
    current_branch = current_build_info.branch

    if not _branch_visibility(current_branch):
        return None

    return _new_version_available(current_build_info, available_downloads, widgets)


def _branch_visibility(current_branch: str) -> bool:
    """
    Check if the current branch is visible based on the settings.
    """
    stable_update_button_visibility = (
        get_show_stable_update_button() if get_use_advanced_update_button() else get_show_update_button()
    )
    daily_update_button_visibility = (
        get_show_daily_update_button() if get_use_advanced_update_button() else get_show_update_button()
    )
    experimental_update_button_visibility = (
        get_show_experimental_update_button() if get_use_advanced_update_button() else get_show_update_button()
    )
    bfa_update_button_visibility = (
        get_show_bfa_update_button() if get_use_advanced_update_button() else get_show_update_button()
    )

    if (current_branch == "stable" or current_branch == "lts") and stable_update_button_visibility:
        return True
    elif current_branch == "daily" and daily_update_button_visibility:
        return True
    elif any(current_branch.startswith(prefix) for prefix in ["Pr", "Npr"]) and experimental_update_button_visibility:
        return True
    elif current_branch == "bforartists" and bfa_update_button_visibility:
        return True
    return False


def _new_version_available(
    current_build_info: BuildInfo,
    available_downloads: List[Any],
    widgets: Any,
) -> Optional[Any]:
    """
    Find available updates
    """
    current_version = current_build_info.semversion.replace(prerelease=None)
    current_branch = current_build_info.branch
    current_hash = current_build_info.build_hash

    installed_hashes = {widget.build_info.build_hash for widget in widgets}
    installed_versions = {widget.build_info.semversion.replace(prerelease=None) for widget in widgets}

    update_behavior = _get_update_behavior(current_branch)
    best_download = None
    best_version = Version(0, 0, 0)

    def is_better_version(download_version: Version) -> bool:
        """
        Check if the download version is greater that the highest installed version
        """
        if update_behavior == 0:
            highest_version = max(installed_versions, default=Version.parse("0.0.0"))
            return download_version.compare(str(highest_version)) > 0

        if download_version.major != current_version.major:
            return False

        if update_behavior == 1:
            filter = current_version.major
            highest_version = max([v for v in installed_versions if v.major == filter], default=Version.parse("0.0.0"))
            return download_version.minor > highest_version.minor or (
                download_version.minor == highest_version.minor and download_version.patch > highest_version.patch
            )

        if download_version.minor != current_version.minor:
            return False

        if update_behavior == 2:
            filter_major = current_version.major
            filter_minor = current_version.minor
            highest_version = max(
                [v for v in installed_versions if v.major == filter_major and v.minor == filter_minor],
                default=Version.parse("0.0.0"),
            )

            return download_version.patch > highest_version.patch

        return False

    for download in available_downloads:
        download_build_info: BuildInfo = download.build_info
        download_version = download_build_info.semversion.replace(prerelease=None)
        download_branch = download_build_info.branch
        download_hash = download_build_info.build_hash

        # Skip if the download is not for the current branch
        if current_branch != download_branch:
            continue

        # Skip if the download hash is already installed
        if download_hash and download_hash in installed_hashes:
            continue

        # Skip if the download version is already installed
        if not download_hash and download_version in installed_versions:
            continue

        if is_better_version(download_version):
            if download_version.compare(str(best_version)) > 0:
                best_version = download_version
                best_download = download

    # If no better version found, check for a new hash version in case the a new build exist for the same version
    if best_download is None:
        for download in available_downloads:
            download_build_info: BuildInfo = download.build_info
            download_hash = download_build_info.build_hash
            download_verison = download_build_info.semversion
            download_branch = download_build_info.branch
            download_timestamp = download_build_info.commit_time

            if current_branch != download_branch:
                continue

            # Skip if the download version is not the same
            if download_verison.replace(prerelease=None).compare(str(current_version)) != 0:
                continue

            # For daily, check if the pre-release flag is higher or not, to prevent updating to older vesrion
            if current_branch == "daily":
                if download_verison.compare(str(current_build_info.semversion)) == -1:
                    continue

            # Skip if the version is not newer
            if download_timestamp <= current_build_info.commit_time:
                continue

            if best_download is not None:
                if download_timestamp > best_download.build_info.commit_time:
                    best_download = download
            else:
                best_download = download

    if best_download is not None:
        logger.info(
            f"Found new hash version {best_download.build_info.build_hash} available for {current_version} in the {current_branch} branch. "
        )

    if best_version.compare("0.0.0") > 0:
        logger.info(
            f"Found new version {best_version} available for {current_version} in the {current_branch} branch. "
        )

    return best_download


def _get_update_behavior(
    current_branch: str,
) -> int:
    """
    0: Major
    1: Minor
    2: Patch
    """
    stable_update_behavior = get_stable_update_behavior() if get_use_advanced_update_button() else get_update_behavior()
    daily_update_behavior = get_daily_update_behavior() if get_use_advanced_update_button() else get_update_behavior()
    experimental_update_behavior = (
        get_experimental_update_behavior() if get_use_advanced_update_button() else get_update_behavior()
    )
    bfa_update_behavior = get_bfa_update_behavior() if get_use_advanced_update_button() else get_update_behavior()

    if current_branch == "stable" or current_branch == "lts":
        return stable_update_behavior
    elif current_branch == "daily":
        return daily_update_behavior
    elif any(current_branch.startswith(prefix) for prefix in ["Pr", "Npr"]):
        return experimental_update_behavior
    elif current_branch == "bforartists":
        return bfa_update_behavior
