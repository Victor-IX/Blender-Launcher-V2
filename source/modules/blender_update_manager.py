from __future__ import annotations

import logging

from semver import Version, compare
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
    current_branch = current_build_info.branch

    if not _branch_visibility(current_branch):
        return None

    return _new_version_available(current_build_info, available_downloads, widgets)


def _branch_visibility(current_branch: str) -> bool:
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

    if (current_branch == "stable" or current_branch == "LTS") and stable_update_button_visibility:
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
    current_version = current_build_info.semversion
    current_branch = current_build_info.branch
    current_hash = current_build_info.build_hash

    installed_hashes = {widget.build_info.build_hash for widget in widgets}
    installed_versions = {widget.build_info.semversion.replace(prerelease=None) for widget in widgets}

    update_behavior = _get_update_behavior(current_branch)
    best_download = None
    best_version = Version(0, 0, 0)

    def is_better_version(download_version: Version) -> bool:
        if update_behavior == 0:
            return compare(str(download_version), str(current_version)) > 0

        if download_version.major != current_version.major:
            return False

        if update_behavior == 1:
            return download_version.minor > current_version.minor or (
                download_version.minor == current_version.minor and download_version.patch > current_version.patch
            )

        if update_behavior == 2:
            return download_version.minor == current_version.minor and download_version.patch > current_version.patch

        return False

    for download in available_downloads:
        download_build_info = download.build_info
        download_version = download_build_info.semversion
        download_branch = download_build_info.branch
        download_hash = download_build_info.build_hash

        if current_branch != download_branch:
            continue

        if download_hash and download_hash in installed_hashes:
            continue
        if not download_hash and download_version in installed_versions:
            continue

        if is_better_version(download_version):
            if compare(str(download_version), str(best_version)) > 0:
                best_version = download_version
                best_download = download

    if best_download is None:
        for download in available_downloads:
            download_hash = download.build_info.build_hash
            if (
                current_branch == download.build_info.branch
                and compare(str(download.build_info.semversion), str(current_version)) == 0
                and download_hash != current_hash
                if download_hash
                else False
            ):
                best_download = download
                logger.info(
                    f"Found new hash version {download.build_info.semversion} available for {current_version} in the {current_branch} branch. "
                )
                break

    if compare(str(best_version), "0.0.0") > 0:
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

    if current_branch == "stable":
        return stable_update_behavior
    elif current_branch == "daily":
        return daily_update_behavior
    elif any(current_branch.startswith(prefix) for prefix in ["Pr", "Npr"]):
        return experimental_update_behavior
    elif current_branch == "bforartists":
        return bfa_update_behavior
