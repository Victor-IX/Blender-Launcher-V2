import datetime
import os
import sys
from pathlib import Path

import pytest
from semver import Version

from source.modules.build_info import BuildInfo, read_blender_version
from tests.config import TESTED_BUILD


@pytest.mark.skipif(
    TESTED_BUILD is None or not os.path.exists(TESTED_BUILD),
    reason="valid testing build is not provided",
)
def test_read_blender_version():
    assert TESTED_BUILD is not None
    pth = Path(TESTED_BUILD)
    read_blender_version(pth)
    # success if no exception


def test_buildinfo_comparisons_and_equality():
    before = datetime.datetime(2024, 12, 31, tzinfo=datetime.UTC)
    after = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
    assert BuildInfo("", "1.0.0", "", before, "") < BuildInfo("", "1.0.1", "", before, "")
    assert BuildInfo("", "1.0.0", "", before, "") < BuildInfo("", "1.0.0", "", after, "")
    assert BuildInfo("", "1.0.0", "hash", before, "") == BuildInfo("", "1.0.0", "hash", before, "")
    assert BuildInfo("", "1.0.0", "hash", before, "") != BuildInfo("", "1.0.0", "", before, "")
    assert BuildInfo("", "1.0.0", None, before, "") == BuildInfo("", "1.0.0", None, before, "")
    assert BuildInfo("", "1.0.0-daily", None, before, "") == BuildInfo("", "1.0.0", None, before, "")


def test_display_version_edge_cases():
    assert BuildInfo._display_version(Version(4, 4, 0)) == "4.4.0"
    assert BuildInfo._display_version(Version(4, 4, 0, prerelease="alpha")) == "4.4.0"
    assert BuildInfo._display_version(Version(2, 79, 75)) == "2.79"
    assert BuildInfo._display_version(Version(2, 79, 75, prerelease="a")) == "2.79a"
    assert BuildInfo._display_version(Version(2, 79, 0, prerelease="b")) == "2.79b"
    assert BuildInfo._display_version(Version(2, 83, 0, prerelease="alpha")) == "2.83alpha"


def test_display_label_variants():
    # NGL the _display_label logic is kinda confusing
    assert BuildInfo._display_label("lts", Version(0, 0, 1), "") == "LTS"
    assert (
        BuildInfo._display_label("experimental", Version(4, 4, 0, prerelease="npr-prototypers"), "4.4.0-npr-prototype")
        == "Npr Prototypers"
    )
    assert BuildInfo._display_label("experimental", Version(4, 4, 0), "4.4.0-npr-prototype") == "Npr-Prototype"
    assert BuildInfo._display_label("daily", Version(2, 80, 0, prerelease="rc2"), "2.80.0-rc2") == "Rc2"
    assert BuildInfo._display_label("daily", Version(2, 80, 0), "2.80.0-rc2") == "Rc2"
    assert (
        BuildInfo._display_label("stable", Version(2, 80, 0, prerelease="rc2"), "2.80.0-rc2") == "Release Candidate 2"
    )
    # Build variant case -- this could possibly be removed
    p = sys.platform
    sys.platform = "darwin"
    assert BuildInfo._display_label("stable", Version(2, 80, 0, prerelease="intel"), "2.80.0-rc2") == "Stable - intel"
    sys.platform = p
