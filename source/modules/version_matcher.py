from __future__ import annotations

import contextlib
import datetime
import os
import re
from dataclasses import dataclass
from functools import cache
from operator import attrgetter
from typing import TYPE_CHECKING

from semver import Version

if TYPE_CHECKING:
    from collections.abc import Sequence

    from modules.build_info import BuildInfo

utc = datetime.UTC


@dataclass(frozen=True)
class BasicBuildInfo:
    version: Version
    branch: str
    build_hash: str
    commit_time: datetime.datetime

    @property
    def major(self):
        return self.version.major

    @property
    def minor(self):
        return self.version.minor

    @property
    def patch(self):
        return self.version.patch

    def __lt__(self, other: BasicBuildInfo):
        if self.version == other.version:
            return self.commit_time < other.commit_time

        return self.version < other.version

    @classmethod
    def from_buildinfo(cls, buildinfo: BuildInfo):
        return BasicBuildInfo(
            version=buildinfo.full_semversion,
            branch=buildinfo.branch,
            build_hash=buildinfo.build_hash if buildinfo.build_hash is not None else "",
            commit_time=buildinfo.commit_time.astimezone(utc),
        )


# VersionSearchQuerySyntax (NOT SEMVER COMPATIBLE!):

# ^   | match the largest/newest item in that column
# *   | match any number in that column
# -   | match the smallest/oldest item in that column
# <n> | match an item in that column

VERSION_SEARCH_SYNTAX = "<major_num>.<minor>.<patch>[-<branch>][+<build_hash>][@<commit time>]"

# Valid examples of version search queries are:
# *.*.*
# 1.2.3-master
# 4.^.^-stable@^
# 4.3.^+cb886aba06d5@^
# 4.3.^@2024-07-31T23:53:51+00:00
# And of course, a full example:
# 4.3.^-stable+cb886aba06d5@2024-07-31T23:53:51+00:00

VERSION_SEARCH_REGEX = re.compile(
    r"""^
    ([\^\-\*]|\d+)\.([\^\-\*]|\d+)\.([\^\-\*]|\d+)
    (?:\-([^\@\s\+]+))?
    (?:\+([\d\w]+))?
    (?:\@([\^\-\*]|[\dT\+\:Z\ \^\-]+))?
    $""",
    flags=re.X,
)

# Regex breakdown:
# ^                                     -- start of string
# ([\^\-\*]|\d+)                     x3 -- major, minor, and patch (required)
# (?:\-([^\@\s\+]+))?                   -- branch (optional)
# (?:\+([\d\w]+))?                      -- build hash (optional)
# (?:\@([\dT\+\:Z\ \^\*\-]+))?            -- commit time (saved as ^|*|- or an isoformat) (optional)
# $                                     -- end of string


VALID_QUERIES = """^.^.*
*.*.14
*.*.*
^.*.*
-.*.^
4.2.^
4.^.^"""
VALID_FULL_QUERIES = """*.*.*
1.2.3-master
4.^,^-stable@^
4.3.^+cb886aba06d5@^
4.3.^@2024-07-31T23:53:51+00:00
4.3.^-stable+cb886aba06d5@2024-07-31T23:53:51+00:00
"""


@cache
def _parse(s: str) -> tuple[int | str, int | str, int | str, str | None, str | None, datetime.datetime | str]:
    """Parse a query from a string. does not support branch and commit_time"""
    match = VERSION_SEARCH_REGEX.match(s)
    if not match:
        raise ValueError(f"Invalid version search query: {s}")

    major = match.group(1)
    minor = match.group(2)
    patch = match.group(3)
    branch = match.group(4)
    build_hash = match.group(5)
    commit_time = match.group(6)
    if commit_time is None:
        commit_time = "^"

    if major.isnumeric():
        major = int(major)
    if minor.isnumeric():
        minor = int(minor)
    if patch.isnumeric():
        patch = int(patch)

    if commit_time is not None and commit_time not in ("^", "*", "-"):
        # Try to convert it to a datetime, and just passing it upon failure
        with contextlib.suppress(ValueError):
            commit_time = datetime.datetime.fromisoformat(commit_time)

    return major, minor, patch, branch, build_hash, commit_time


@dataclass(frozen=True)
class VersionSearchQuery:
    """A dataclass for a search query. The attributes are ordered by priority"""

    major: int | str
    "A major release of Blender"

    minor: int | str
    "A minor release of Blender"

    patch: int | str
    "A patch release of Blender"

    branch: str | tuple[str, ...] | None = None
    "Which branch of Blender this is (stable, daily, experimental, etc.)"

    build_hash: str | None = None
    "The git hash of the build that this is"

    commit_time: datetime.datetime | str = "^"
    "When the build was made (in UTC)"

    def __post_init__(self):
        for pos in (self.major, self.minor, self.patch, self.commit_time):
            if isinstance(pos, str) and pos not in ["^", "*", "-"]:
                raise ValueError(f'{pos} must be in ["^", "*", "-"]')
        if self.build_hash and self.build_hash in ["^", "-"]:
            raise ValueError("build_hash cannot be temporally matched")
        if self.branch and self.branch in ["^", "-"]:
            raise ValueError("branch cannot be temporally matched")

    @classmethod
    def parse(cls, s: str):
        """Parse a query from a string. does not support branch and commit_time"""

        return cls(*_parse(s))

    @classmethod
    def default(cls):
        return cls("^", "^", "^", commit_time="^", branch=None)

    @classmethod
    def any(cls):
        return cls("*", "*", "*", commit_time="*", branch=None)

    def __str__(self) -> str:
        """Returns a string that can be parsed by parse()"""
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.branch:
            s += f"-{self.branch}"
        if self.build_hash:
            s += f"+{self.build_hash}"
        if self.commit_time:
            s += f"@{self.commit_time}"
        return s

    def with_branch(self, branch: str | tuple[str, ...] | None = None):
        return self.__class__(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            branch=branch,
            build_hash=self.build_hash,
            commit_time=self.commit_time,
        )

    def with_build_hash(self, build_hash: str | None = None):
        return self.__class__(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            branch=self.branch,
            build_hash=build_hash,
            commit_time=self.commit_time,
        )

    def with_commit_time(self, commit_time: datetime.datetime | str):
        return self.__class__(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            branch=self.branch,
            build_hash=self.build_hash,
            commit_time=commit_time,
        )

    def match(self, versions: list[BasicBuildInfo]) -> list[BasicBuildInfo]:
        return match_versions(self, versions)


# Examples:
# VersionSearchQuery("^", "^", "^"): Match the latest version(s)
# VersionSearchQuery(4, "^", "^"): Match the latest version of major 4
# VersionSearchQuery("^", "*", "*"): Match any version in the latest major release

@dataclass(frozen=True)
class BInfoMatcher:
    versions: tuple[BasicBuildInfo, ...]

    def match(self, s: VersionSearchQuery) -> tuple[BasicBuildInfo, ...]:
        return tuple(match_versions(s, list(self.versions)))


def match_versions(s: VersionSearchQuery, versions: list[BasicBuildInfo]) -> list[BasicBuildInfo]:
    for place in ("build_hash", "major", "minor", "patch", "branch", "commit_time"):
        getter = attrgetter(place)
        p: str | tuple[str, ...] | int | datetime.datetime | None = getter(s)
        if p == "*" or p is None:
            continue  # all versions match
        if p == "^":
            # get the max number for `place` in version
            max_p = max(getter(v) for v in versions)

            versions = [v for v in versions if getter(v) == max_p]
        elif p == "-":
            # get the min number for `place` in version
            min_p = min(getter(v) for v in versions)

            versions = [v for v in versions if getter(v) == min_p]
        elif isinstance(p, tuple):
            versions = [v for v in versions if any(getter(v) == q for q in p)]
        else:
            versions = [v for v in versions if getter(v) == p]

        if not versions:
            return versions
    return versions


if __name__ == "__main__" or "PYTEST_VERSION" in os.environ:  # Test BInfoMatcher
    builds = (
        BasicBuildInfo(Version.parse("1.2.3"), "stable", "", datetime.datetime(2020, 5, 4, tzinfo=utc)),
        BasicBuildInfo(Version.parse("1.2.2"), "stable", "", datetime.datetime(2020, 4, 2, tzinfo=utc)),
        BasicBuildInfo(Version.parse("1.2.1"), "daily", "", datetime.datetime(2020, 3, 1, tzinfo=utc)),
        BasicBuildInfo(Version.parse("1.2.4"), "stable", "", datetime.datetime(2020, 6, 3, tzinfo=utc)),
        BasicBuildInfo(Version.parse("3.6.14"), "lts", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
        BasicBuildInfo(Version.parse("4.2.0"), "stable", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
        BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 30, tzinfo=utc)),
        BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 28, tzinfo=utc)),
        BasicBuildInfo(Version.parse("4.3.1"), "daily", "", datetime.datetime(2024, 7, 20, tzinfo=utc)),
    )

    matcher = BInfoMatcher(builds)

    def test_binfo_matcher():
        # find the latest minor builds with any patch number
        results = matcher.match(VersionSearchQuery("^", "^", "*", commit_time="*"))
        assert results == (
            BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 30, tzinfo=utc)),
            BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 28, tzinfo=utc)),
            BasicBuildInfo(Version.parse("4.3.1"), "daily", "", datetime.datetime(2024, 7, 20, tzinfo=utc)),
        )

        # find any version with a patch of 14
        results = matcher.match(VersionSearchQuery("*", "*", 14))
        assert results == (
            BasicBuildInfo(Version.parse("3.6.14"), "lts", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
        )

        # find any version in the lts branch
        results = matcher.match(VersionSearchQuery("*", "*", "*", branch="lts"))
        assert results == (
            BasicBuildInfo(Version.parse("3.6.14"), "lts", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
        )

        # find the latest daily builds for the latest major release
        results = matcher.match(VersionSearchQuery("^", "*", "*", branch="daily", commit_time="^"))
        assert results == (
            BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 30, tzinfo=utc)),
        )

        # find oldest major release with any minor and largest patch
        results = matcher.match(VersionSearchQuery("-", "*", "^"))
        assert results == (
            BasicBuildInfo(Version.parse("1.2.4"), "stable", "", datetime.datetime(2020, 6, 3, tzinfo=utc)),
        )

        print("test_binfo_matcher successful!")

    def test_vsq_serialization():
        import json

        for query in (
            VersionSearchQuery("^", "^", "*"),
            VersionSearchQuery("*", "*", 14),
            VersionSearchQuery("*", "*", "*", branch="lts"),
            VersionSearchQuery("^", "*", "*", branch="daily", commit_time="^"),
            VersionSearchQuery("-", "*", "^"),
            VersionSearchQuery(4, 0, 0),
            VersionSearchQuery(4, "*", "*"),
            VersionSearchQuery("^", "^", "*", branch="stable", commit_time=datetime.datetime(2020, 5, 4, tzinfo=utc)),
        ):
            result_before_serialization = matcher.match(query)

            serialized_query = str(query)
            print(serialized_query)
            deserialized_query = VersionSearchQuery.parse(serialized_query)
            print(deserialized_query)

            result_after_serialization = matcher.match(deserialized_query)

            assert result_before_serialization == result_after_serialization

        print("test_vsq_serialization successful!")

    def test_search_query_parser():
        # Test parsing of search query strings
        assert VersionSearchQuery.parse("1.2.3") == VersionSearchQuery(1, 2, 3)
        assert VersionSearchQuery.parse("^.*.-") == VersionSearchQuery("^", "*", "-")
        assert VersionSearchQuery.parse("*.*.*-daily") == VersionSearchQuery("*", "*", "*", branch="daily")
        assert VersionSearchQuery.parse("*.*.*+cb886aba06d5") == VersionSearchQuery(
            "*", "*", "*", build_hash="cb886aba06d5"
        )
        assert VersionSearchQuery.parse("*.*.*@2024-07-31T23:53:51+00:00") == VersionSearchQuery(
            "*", "*", "*", commit_time=datetime.datetime(2024, 7, 31, 23, 53, 51, tzinfo=utc)
        )
        assert VersionSearchQuery.parse("*.*.*@2024-07-31 23:53:51+00:00") == VersionSearchQuery(
            "*", "*", "*", commit_time=datetime.datetime(2024, 7, 31, 23, 53, 51, tzinfo=utc)
        )
        # Test parsing of search query strings that are not valid
        try:
            VersionSearchQuery.parse("abc")
            raise AssertionError("Expected ValueError to be raised")
        except ValueError:
            pass

        print("test_search_query_parser successful!")

    test_binfo_matcher()
    test_vsq_serialization()
    test_search_query_parser()
