from __future__ import annotations

from dataclasses import dataclass
from operator import attrgetter
from typing import TYPE_CHECKING

from modules.build_info import BuildInfo

if TYPE_CHECKING:
    from datetime import datetime

    from semver import Version


@dataclass(frozen=True)
class BasicBuildInfo:
    version: Version
    commit_time: datetime
    branch: str

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
            version=buildinfo.full_semversion, commit_time=buildinfo.commit_time, branch=buildinfo.branch
        )


# ^   | match the largest number in that column
# *   | match any number in that column
# -   | match the smallest number in that column
# <n> | match a number in that column


@dataclass(frozen=True)
class VersionSearchQuery:
    major: int | str
    minor: int | str
    patch: int | str
    commit_time: datetime | str | None = None
    branch: str | None = None

    def __post_init__(self):
        for pos in (self.major, self.minor, self.patch, self.commit_time):
            if isinstance(pos, str) and pos not in ["^", "*", "-"]:
                raise ValueError(f'{pos} must be in ["^", "*", "-"]')

    @classmethod
    def default(cls):
        return cls("^", "^", "^", commit_time="^", branch=None)


# Examples:
# VersionSearchQuery("^", "^", "^"): Match the latest version(s)
# VersionSearchQuery(4, "^", "^"): Match the latest version of major 4
# VersionSearchQuery("^", "*", "*"): Match any version in the latest major release


@dataclass(frozen=True)
class BInfoMatcher:
    versions: tuple[BasicBuildInfo, ...]

    def match(self, s: VersionSearchQuery) -> tuple[BasicBuildInfo, ...]:
        versions = self.versions

        for place in ("major", "minor", "patch", "commit_time", "branch"):
            getter = attrgetter(place)
            p: str | int | datetime | None = getter(s)
            if p == "^":
                # get the max number for `place` in version
                max_p = max(getter(v) for v in versions)

                versions = [v for v in versions if getter(v) == max_p]
            elif p == "*" or p is None:
                pass  # all versions match
            elif p == "-":
                # get the min number for `place` in version
                min_p = min(getter(v) for v in versions)

                versions = [v for v in versions if getter(v) == min_p]
            else:
                versions = [v for v in versions if getter(v) == p]

            if len(versions) == 1:
                return tuple(versions)

        return tuple(versions)


if __name__ == "__main__":  # Test BInfoMatcher
    import json
    from pprint import pprint

    from threads.library_drawer import get_blender_builds

    BBI = BasicBuildInfo
    versions = []
    for build, _ in get_blender_builds(("stable", "daily", "experimental", "custom")):
        if (pth := (build / ".blinfo")).exists():
            with pth.open(encoding="utf-8") as f:
                data = json.load(f)
            info = BuildInfo.from_dict(str(pth), data["blinfo"][0])
            binfo = BasicBuildInfo.from_buildinfo(info)

            versions.append(binfo)

        print(build)

    matcher = BInfoMatcher(tuple(versions))
    search = VersionSearchQuery("^", "^", "*")


    pprint(sorted(matcher.match(search)))
