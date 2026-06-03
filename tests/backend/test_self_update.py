"""Tests for the launcher self-update asset resolution and naming.

These guard against the macOS regression where the download URL was built as
``..._macOS_x64.zip`` while the release workflow publishes ``..._macos_arm64.zip``.
"""

import sys

import pytest

from source.modules import platform_utils
from source.windows.update_window import release_asset_url


def test_release_asset_url_windows_matches_workflow():
    # windows_release.yml publishes Blender_Launcher_<tag>_Windows_x64.zip
    url = release_asset_url("v2.7.3", "Windows")
    assert url.endswith("/v2.7.3/Blender_Launcher_v2.7.3_Windows_x64.zip")


def test_release_asset_url_macos_matches_workflow():
    # macos_release.yml publishes Blender_Launcher_<tag>_macos_arm64.zip (lowercase)
    url = release_asset_url("v2.7.3", "macOS")
    assert url.endswith("/v2.7.3/Blender_Launcher_v2.7.3_macos_arm64.zip")


@pytest.mark.parametrize(
    ("platform_name", "expected"),
    [
        ("win32", ("Blender Launcher.exe", "Blender Launcher Updater.exe")),
        ("darwin", ("Blender Launcher.app", "Blender Launcher Updater.app")),
        ("linux", ("Blender Launcher", "Blender Launcher Updater")),
    ],
)
def test_get_launcher_name_per_platform(monkeypatch, platform_name, expected):
    monkeypatch.setattr(sys, "platform", platform_name)
    platform_utils.get_launcher_name.cache_clear()
    try:
        assert platform_utils.get_launcher_name() == expected
    finally:
        platform_utils.get_launcher_name.cache_clear()
