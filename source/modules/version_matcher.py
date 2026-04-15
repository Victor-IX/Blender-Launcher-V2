from __future__ import annotations

import contextlib
import datetime
import re
from dataclasses import dataclass, replace
from functools import cache, lru_cache
from operator import attrgetter
from typing import TYPE_CHECKING, Self, TypedDict, Unpack

if TYPE_CHECKING:
    from collections.abc import Iterable

    from modules.build_info import BuildInfo
    from semver import Version

utc = datetime.UTC


@dataclass(frozen=True)
class BasicBuildInfo:
    version: Version
    branch: str
    build_hash: str
    commit_time: datetime.datetime
    folder: str | None = None
    custom_name: str | None = None

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
    def from_buildinfo(cls, buildinfo: BuildInfo, folder: str | None = None):
        return BasicBuildInfo(
            version=buildinfo.full_semversion,
            branch=buildinfo.branch,
            build_hash=buildinfo.build_hash if buildinfo.build_hash is not None else "",
            commit_time=buildinfo.commit_time.astimezone(utc),
            folder=folder,
            custom_name=buildinfo.custom_name,
        )

    @property
    def fuzzy_text(self) -> str:
        return f"{self.version} {self.branch.casefold()} {self.custom_name.casefold() if self.custom_name is not None else ''} {self.build_hash} {self.commit_time} {self.folder}"


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
4.^.^-stable@^
4.3.^+cb886aba06d5@^
4.3.^@2024-07-31T23:53:51+00:00
4.3.^-stable+cb886aba06d5@2024-07-31T23:53:51+00:00
"""


@cache
def _parse(s: str) -> dict:
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

    if major.isnumeric():
        major = int(major)
    if minor.isnumeric():
        minor = int(minor)
    if patch.isnumeric():
        patch = int(patch)
    if branch is not None:
        branch = tuple(branch.split(","))

    if commit_time is not None and commit_time not in ("^", "*", "-"):
        # Try to convert it to a datetime, and just passing it upon failure
        with contextlib.suppress(ValueError):
            commit_time = datetime.datetime.fromisoformat(commit_time)

    return {
        "build_hash": build_hash,
        "major": major,
        "minor": minor,
        "patch": patch,
        "branch": branch,
        "commit_time": commit_time,
    }


class VSQKwargs(TypedDict, total=False):  # used for kwargs typing
    fuzzy_text: str | None
    folder: str | None
    build_hash: str | None
    major: int | str
    minor: int | str
    patch: int | str
    branch: tuple[str, ...] | None
    commit_time: datetime.datetime | str | None
    after: datetime.datetime | None
    before: datetime.datetime | None


class VSQExtraKwargs(TypedDict, total=False):  # VSQKwargs without major/minor/patch
    folder: str | None
    build_hash: str | None
    branch: tuple[str, ...] | None
    commit_time: datetime.datetime | str | None
    after: datetime.datetime | None
    before: datetime.datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class VersionSearchQuery:
    """A dataclass for a search query. The attributes are ordered by priority"""

    fuzzy_text: str | None = None

    folder: str | None = None

    build_hash: str | None = None
    "The git hash of the build that this is"

    major: int | str = "*"
    "A major release of Blender"

    minor: int | str = "*"
    "A minor release of Blender"

    patch: int | str = "*"
    "A patch release of Blender"

    branch: tuple[str, ...] | None = None
    "Which branch of Blender this is (stable, daily, experimental, etc.)"

    commit_time: datetime.datetime | str | None = None
    "When the build was made (in UTC)"

    after: datetime.datetime | None = None
    "Filter builds after this date"

    before: datetime.datetime | None = None
    "Filter builds before this date"

    def __post_init__(self):
        for pos in (self.major, self.minor, self.patch, self.commit_time):
            if isinstance(pos, str) and pos not in ["^", "*", "-"]:
                raise ValueError(f'{pos} must be in ["^", "*", "-"]')
        if self.build_hash and self.build_hash in ["^", "-"]:
            raise ValueError("build_hash cannot be temporally matched")
        if self.branch and self.branch in ["^", "-"]:
            raise ValueError("branch cannot be temporally matched")

    @classmethod
    def parse(cls, s: str) -> Self:
        """Parse a query from a string. does not support branch and commit_time"""

        return cls(**_parse(s))

    @classmethod
    def version(
        cls,
        major: int | str,
        minor: int | str,
        patch: int | str,
        **extra_args: Unpack[VSQExtraKwargs],
    ):
        """A constructor with major, minor, and patch at the front"""
        return cls(major=major, minor=minor, patch=patch, **extra_args)

    @classmethod
    def default(cls):
        return cls(
            major="^",
            minor="^",
            patch="^",
            commit_time="^",
        )

    @classmethod
    def any(cls):
        return cls()

    def __str__(self) -> str:
        """Returns a string that can be parsed by parse()"""
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.branch:
            s += f"-{','.join(self.branch)}"
        if self.build_hash:
            s += f"+{self.build_hash}"
        if self.commit_time is not None and self.commit_time != "*":
            s += f"@{self.commit_time}"
        return s

    def __or__(self, other: VersionSearchQuery) -> VersionSearchQuery:
        d = {place: getattr(self, place) for place in self.__slots__}
        d.update({place: getattr(other, place) for place in other.relevant_places()})
        return self.__class__(**d)

    def with_fuzzy_text(self, fuzzy_text: str | None = None):
        return replace(self, fuzzy_text=fuzzy_text)

    def with_folder(self, folder: str | None = None):
        return replace(self, folder=folder)

    def with_branch(self, branch: tuple[str, ...] | None = None):
        return replace(self, branch=branch)

    def with_build_hash(self, build_hash: str | None = None):
        return replace(self, build_hash=build_hash)

    def with_commit_time(self, commit_time: datetime.datetime | str | None = None):
        return replace(self, commit_time=commit_time)

    def with_after(self, after: datetime.datetime | None = None):
        return replace(self, after=after)

    def with_before(self, before: datetime.datetime | None = None):
        return replace(self, before=before)

    def relevant_places(self) -> tuple[str, ...]:
        return _relevant_places(self)

    def match(self, versions: Iterable[BasicBuildInfo]) -> list[BasicBuildInfo]:
        return match_versions(self, versions)


@lru_cache(16)
def _relevant_places(vsq: VersionSearchQuery) -> tuple[str, ...]:
    return tuple(place for place in vsq.__slots__ if getattr(vsq, place) not in {"*", None})


# Examples:
# VersionSearchQuery("^", "^", "^"): Match the latest version(s)
# VersionSearchQuery(4, "^", "^"): Match the latest version of major 4
# VersionSearchQuery("^", "*", "*"): Match any version in the latest major release


def match_versions(s: VersionSearchQuery, versions: Iterable[BasicBuildInfo]) -> list[BasicBuildInfo]:
    versions: list[BasicBuildInfo] = list(versions)
    relevant_places = s.relevant_places()
    for place in relevant_places:
        getter = attrgetter(place)
        p: str | tuple[str, ...] | int | datetime.datetime | None = getter(s)
        match (place, p):
            case ("*" | None, _):
                ...  # all versions match (should be unreachable due to relevant_places)
            case ("after", time):
                versions = [v for v in versions if v.commit_time >= time]
            case ("before", time):
                versions = [v for v in versions if v.commit_time <= time]
            case ("fuzzy_text", txt):
                versions = fuzzy_search_by_str(versions, txt)
            case (_, "^"):
                # get the max number for `place` in version
                max_p = max(getter(v) for v in versions)
                versions = [v for v in versions if getter(v) == max_p]
            case (_, "-"):
                # get the min number for `place` in version
                min_p = min(getter(v) for v in versions)
                versions = [v for v in versions if getter(v) == min_p]
            case (_, p) if isinstance(p, tuple):
                versions = [v for v, x in zip(versions, map(getter, versions), strict=True) if any(x == q for q in p)]
            case (_, p):
                versions = [v for v in versions if getter(v) == p]

        if not versions:
            return versions
    return list(versions)


def fuzzy_search_by_str(lst: list[BasicBuildInfo], search: str) -> list[BasicBuildInfo]:
    search = search.casefold()
    from fuzzysearch import Match, find_near_matches

    exact_matches: list[BasicBuildInfo] = []
    close_matches: dict[int, list[BasicBuildInfo]] = {}

    any_matches = False
    l_dist = 0
    while not any_matches and l_dist < 4:
        l_dist += 1
        for b in lst:
            s = b.fuzzy_text.casefold()
            matches: list[Match] = find_near_matches(
                search,
                s,
                max_l_dist=l_dist,
                max_deletions=1,
                max_substitutions=1,
                max_insertions=0,
            )
            if matches:
                any_matches = True
                if any(m.matched == search for m in matches):
                    exact_matches.append(b)
                else:
                    maxdist = max(m.dist for m in matches)
                    close_matches.setdefault(maxdist, []).append(b)

    all_matches = exact_matches
    # prioritize builds that are closer to the target
    for _dist, builds in sorted(close_matches.items()):
        all_matches.extend(builds)

    return all_matches
