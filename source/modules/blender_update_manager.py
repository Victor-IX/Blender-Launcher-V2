from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from modules.settings import (
    get_bfa_update_behavior,
    get_daily_update_behavior,
    get_experimental_update_behavior,
    get_show_bfa_update_button,
    get_show_daily_update_button,
    get_show_experimental_update_button,
    get_show_stable_update_button,
    get_show_upbge_stable_update_button,
    get_show_upbge_weekly_update_button,
    get_show_update_button,
    get_stable_update_behavior,
    get_update_behavior,
    get_upbge_stable_update_behavior,
    get_upbge_weekly_update_behavior,
    get_use_advanced_update_button,
)
from semver import Version

if TYPE_CHECKING:
    from modules.build_info import BuildInfo

logger = logging.getLogger()


def available_blender_update(
    current_build_info: BuildInfo,
    available_downloads: list[Any],
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
    upbge_stable_update_button_visibility = (
        get_show_upbge_stable_update_button() if get_use_advanced_update_button() else get_show_update_button()
    )
    upbge_weekly_update_button_visibility = (
        get_show_upbge_weekly_update_button() if get_use_advanced_update_button() else get_show_update_button()
    )

    if current_branch in {"stable", "lts"} and stable_update_button_visibility:
        return True
    elif current_branch == "daily" and daily_update_button_visibility:
        return True
    elif any(current_branch.startswith(prefix) for prefix in ["Pr", "Npr"]) and experimental_update_button_visibility:
        return True
    elif current_branch == "bforartists" and bfa_update_button_visibility:
        return True
    elif current_branch == "upbge-stable" and upbge_stable_update_button_visibility:
        return True
    elif current_branch == "upbge-weekly" and upbge_weekly_update_button_visibility:
        return True
    return False


def _new_version_available(
    current_build_info: BuildInfo,
    available_downloads: list[Any],
    widgets: Any,
) -> Any | None:
    """Find available updates based on version or newer builds of same version."""
    current_version = current_build_info.semversion.replace(prerelease=None)
    current_branch = current_build_info.branch

    installed_hashes = {widget.build_info.build_hash for widget in widgets}
    installed_versions = {widget.build_info.semversion.replace(prerelease=None) for widget in widgets}

    update_behavior = _get_update_behavior(current_branch)

    best_version_download = None
    best_version = Version(0, 0, 0)
    best_hash_download = None
    best_hash_timestamp = None

    branch_downloads = [d for d in available_downloads if d.build_info.branch == current_branch]

    for download in branch_downloads:
        build_info = download.build_info

        download_version = build_info.semversion.replace(prerelease=None)
        download_hash = build_info.build_hash

        # Skip already installed versions/hashes
        if download_hash in installed_hashes:
            continue

        if download_version in installed_versions and not _is_newer_build(build_info, current_build_info):
            continue

        # Check for version updates
        if _is_better_version(download_version, current_version, installed_versions, update_behavior):
            if download_version.compare(str(best_version)) > 0:
                best_version = download_version
                best_version_download = download

        # Check for hash updates for same version
        elif (
            download_version.compare(str(current_version)) == 0
            and build_info.commit_time > current_build_info.commit_time
        ):
            # For daily builds, verify if version isn't older (check with pre-release flag)
            if current_branch == "daily" and build_info.semversion.compare(str(current_build_info.semversion)) < 0:
                continue

            if best_hash_timestamp is None or build_info.commit_time > best_hash_timestamp:
                best_hash_timestamp = build_info.commit_time
                best_hash_download = download

    if best_version_download:
        logger.info(f"Found new version {best_version} available for {current_version} in the {current_branch} branch.")
        return best_version_download

    if best_hash_download:
        logger.info(
            f"Found new hash version {best_hash_download.build_info.build_hash} "
            f"available for {current_version} in the {current_branch} branch."
        )
        return best_hash_download

    return None


def _is_better_version(
    download_version: Version, current_version: Version, installed_versions: set, update_behavior: int
) -> bool:
    """Check if download version is better according to update behavior."""
    # Major update (behavior 0): Any higher version
    if update_behavior == 0:
        highest_version = max(installed_versions, default=Version.parse("0.0.0"))
        return download_version.compare(str(highest_version)) > 0

    # Skip major diff
    if download_version.major != current_version.major:
        return False

    # Minor update (behavior 1): Same major, higher minor/patch
    if update_behavior == 1:
        highest_version = max(
            (v for v in installed_versions if v.major == current_version.major), default=Version.parse("0.0.0")
        )
        return download_version.minor > highest_version.minor or (
            download_version.minor == highest_version.minor and download_version.patch > highest_version.patch
        )

    # Skip minor diff
    if download_version.minor != current_version.minor:
        return False

    # Patch update (behavior 2): Same major.minor, higher patch
    if update_behavior == 2:
        highest_version = max(
            (v for v in installed_versions if v.major == current_version.major and v.minor == current_version.minor),
            default=Version.parse("0.0.0"),
        )
        return download_version.patch > highest_version.patch

    return False


def _is_newer_build(download_info: BuildInfo, current_info: BuildInfo) -> bool:
    """Check if download is a newer build of the same version."""
    return download_info.commit_time > current_info.commit_time


def is_major_version_update(current_build_info: BuildInfo, update_download) -> bool:
    """Check if the update is a major or minor version change."""

    current_version = current_build_info.semversion.replace(prerelease=None)
    update_version = update_download.build_info.semversion.replace(prerelease=None)

    return update_version.major != current_version.major or update_version.minor != current_version.minor


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
    upbge_stable_update_behavior = (
        get_upbge_stable_update_behavior() if get_use_advanced_update_button() else get_update_behavior()
    )
    upbge_weekly_update_behavior = (
        get_upbge_weekly_update_behavior() if get_use_advanced_update_button() else get_update_behavior()
    )

    if current_branch in {"stable", "lts"}:
        return stable_update_behavior
    elif current_branch == "daily":
        return daily_update_behavior
    elif any(current_branch.startswith(prefix) for prefix in ["Pr", "Npr"]):
        return experimental_update_behavior
    elif current_branch == "bforartists":
        return bfa_update_behavior
    elif current_branch == "upbge-stable":
        return upbge_stable_update_behavior
    elif current_branch == "upbge-weekly":
        return upbge_weekly_update_behavior

    return get_update_behavior()
