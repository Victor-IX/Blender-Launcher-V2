from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from modules.blender_update_manager import _new_version_available
from modules.build_info import BuildInfo
from modules.scraper_cache import ScraperCache
from semver import Version
from threads.scraping import bfa

STABLE = b"""<details><summary>Bforartists 5.2.0 (5 files)</summary>
<a href="Bforartists-5.2.0-Windows.zip">Windows</a>
<a href="Bforartists-5.2.0-Windows.zip">Duplicate</a>
<a href="Bforartists-5.2.0-Mac-Intel.dmg">Intel</a>
<a href="Bforartists-5.2.0-Mac-Silicon.dmg">Silicon</a>
<a href="Bforartists-5.2.0-Linux.tar.xz">Linux</a>
<a href="Install.exe">Installer</a>
<a href="https://example.com/unwanted-Windows.zip">External</a>
</details>"""
DEV = b"""<details><summary>2026-10-27 <span>2 files</span></summary>
<a href="builds/windows-devbuild-27-10-2026.zip">Windows</a>
<a href="builds/linux-devbuild-27-10-2026.tar.xz">Linux</a>
</details><details><summary>2026-99-99</summary><a href="bad.zip">Bad</a></details>"""
DATE = datetime(2026, 10, 19, tzinfo=UTC)


def response(data=b"", status=200):
    return Mock(data=data, status=status, headers={"Last-Modified": "Mon, 19 Oct 2026 00:00:00 GMT"})


@pytest.fixture
def scraper(monkeypatch, tmp_path):
    monkeypatch.setattr(bfa, "bfa_cache_path", lambda: tmp_path / "bfa.json")
    monkeypatch.setattr(bfa, "get_platform", lambda: "Windows")
    manager = Mock()
    manager.request.side_effect = lambda method, url: (
        response() if method == "HEAD" else response(STABLE if url == bfa.BFA_DOWNLOADS_URL else DEV)
    )
    return bfa.ScraperBfa(manager)


@pytest.mark.parametrize(
    ("platform", "architecture", "suffix", "count"),
    [
        ("Windows", "amd64", "Windows.zip", 2),
        ("Linux", "amd64", "Linux.tar.xz", 2),
        ("macOS", "arm64", "Mac-Silicon.dmg", 1),
        ("macOS", "amd64", "Mac-Intel.dmg", 1),
    ],
)
def test_indexes(scraper, monkeypatch, platform, architecture, suffix, count):
    monkeypatch.setattr(bfa, "get_platform", lambda: platform)
    monkeypatch.setattr(bfa, "get_architecture", lambda: architecture)
    builds = list(scraper.scrape())
    assert len(builds) == count
    assert builds[0].link == bfa.BFA_DOWNLOADS_URL + "Bforartists-5.2.0-" + suffix
    assert builds[0].commit_time == DATE
    assert builds[0].is_valid()
    if count == 2:
        assert builds[1].is_bfa_dev
        assert builds[1].display_version == "Dev"
        assert builds[1].commit_time == datetime(2026, 10, 27, tzinfo=UTC)
        assert builds[1] != builds[0]


def test_replaces_legacy_cache_and_reuses_new_timestamps(scraper):
    old = BuildInfo("https://cloud.bforartists.de/old.zip", "5.2.0", None, DATE, "bforartists")
    scraper.cache.new_build(Version(5, 2, 0), DATE).assets.append(old)
    builds = list(scraper.scrape())
    saved = ScraperCache.from_file_or_default(scraper.cache_path)
    assert all("cloud.bforartists.de" not in a.link for f in saved.folders.values() for a in f.assets)
    scraper.manager.reset_mock()
    assert list(scraper.scrape()) == builds
    assert all(call.args[0] == "GET" for call in scraper.manager.request.call_args_list)


def test_failed_index_does_not_hide_other_repository(scraper):
    scraper.manager.request.side_effect = lambda method, url: (
        response(status=503) if url == bfa.BFA_DOWNLOADS_URL else response(DEV)
    )
    builds = list(scraper.scrape())
    assert len(builds) == 1 and builds[0].is_bfa_dev


def test_no_wrong_architecture_fallback(monkeypatch):
    from pathlib import PurePosixPath

    monkeypatch.setattr(bfa, "get_architecture", lambda: "amd64")
    assert bfa.ScraperBfa.filter_macos_candidates([(PurePosixPath("Mac-Silicon.dmg"), DATE)]) == []


def test_legacy_windows_archives_and_source_exclusion(scraper):
    assert scraper.matches_platform("bforartists3_322.zip")
    assert scraper.matches_platform("bforartists_win64_100.zip")
    assert not scraper.matches_platform("bforartists_win32_100.zip")
    assert not scraper.matches_platform("Bforartists_master_100.zip")


def test_developer_identity_and_update_isolation(monkeypatch):
    monkeypatch.setattr("modules.blender_update_manager._get_update_behavior", lambda branch: 0)
    stable = BuildInfo("stable", "5.2.0", None, DATE, "bforartists")
    dev = BuildInfo("dev", "0.0.20261027-dev", None, datetime(2026, 10, 27, tzinfo=UTC), "bforartists")
    installed = BuildInfo("installed", "5.3.0-dev", "abc", dev.commit_time, "bforartists")
    assert installed == dev
    assert installed != stable
    assert _new_version_available(stable, [SimpleNamespace(build_info=dev)], []) is None
    assert _new_version_available(installed, [SimpleNamespace(build_info=stable)], []) is None
    older = BuildInfo("older", "5.3.0-dev", "def", DATE, "bforartists")
    download = SimpleNamespace(build_info=dev)
    assert _new_version_available(older, [download], []) is download


def test_installed_developer_metadata_survives_read(monkeypatch, tmp_path):
    from modules.build_info import read_blender_version

    directory = tmp_path / "bforartists" / "Bforartists-5.3.0"
    directory.mkdir(parents=True)
    (directory / "bforartists.exe").touch()
    monkeypatch.setattr("modules.build_info._check_output", lambda args: b"Bforartists 5.3.0\nbuild hash: abc123\n")
    info = BuildInfo("download", "5.3.0-dev", None, DATE, "bforartists", custom_executable="bforartists.exe")
    installed = read_blender_version(directory, info)
    assert installed.is_bfa_dev
    assert installed.commit_time == DATE
    assert installed.subversion == "5.3.0-dev"
    assert installed.custom_executable == "bforartists.exe"
    assert installed == info


@pytest.mark.parametrize(("architecture", "expected"), [("arm64", "Silicon"), ("amd64", "Intel")])
def test_macos_prefers_native_over_universal(monkeypatch, architecture, expected):
    from pathlib import PurePosixPath

    monkeypatch.setattr(bfa, "get_architecture", lambda: architecture)
    candidates = [
        (PurePosixPath(f"Bforartists-4.5.2-Mac-{arch}.dmg"), DATE) for arch in ("Universal", "Intel", "Silicon")
    ]
    selected = bfa.ScraperBfa.filter_macos_candidates(candidates)
    assert len(selected) == 1
    assert expected in selected[0][0].name


@pytest.mark.parametrize(("architecture", "opposite"), [("arm64", "Intel"), ("amd64", "Silicon")])
def test_macos_universal_fallback(monkeypatch, architecture, opposite):
    from pathlib import PurePosixPath

    monkeypatch.setattr(bfa, "get_architecture", lambda: architecture)
    candidates = [(PurePosixPath(f"Mac-{opposite}.dmg"), DATE), (PurePosixPath("Mac-Universal.dmg"), DATE)]
    assert bfa.ScraperBfa.filter_macos_candidates(candidates) == candidates[1:]
