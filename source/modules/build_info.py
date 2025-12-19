from __future__ import annotations

import json
import logging
import re
import sys
import shlex
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path

import dateparser
from modules._platform import _check_output, _popen, get_platform
from modules.bl_api_manager import lts_blender_version, read_blender_version_list
from modules.settings import (
    get_bash_arguments,
    get_blender_startup_arguments,
    get_launch_blender_no_console,
    get_library_folder,
)
from modules.task import Task
from PySide6.QtCore import Signal
from semver import Version

logger = logging.getLogger()


# TODO: Combine some of these
matchers = tuple(
    map(
        re.compile,
        (  #                                                                                   # format                                 examples
            r"(?P<ma>\d+)\.(?P<mi>\d+)\.(?P<pa>\d+)[ \-](?P<pre>[^+]*[^wli][^ndux][^s]?)",  # <major>.<minor>.<patch> <Prerelease>   2.80.0 Alpha  -> 2.80.0-alpha
            # r"(?P<ma>\d+)\.(?P<mi>\d+)\.(?P<pa>\d+)",  #                                       <major>.<minor>.<patch>                3.0.0         -> 3.0.0
            r"(?P<ma>\d+)\.(?P<mi>\d+)[ \-](?P<pre>[^+]*[^wli][^ndux][^s]?)",
            r"(?P<ma>\d+)\.(?P<mi>\d+) \(sub (?P<pa>\d+)\)",  #                                  <major>.<minor> (sub <patch>)          2.80 (sub 75) -> 2.80.75
            r"(?P<ma>\d+)\.(?P<mi>\d+)$",  #                                                     <major>.<minor>                        2.79          -> 2.79.0
            r"(?P<ma>\d+)\.(?P<mi>\d+)(?P<pre>[^-]{0,3})",  #                                    <major>.<minor><[chars]*(1-3)>         2.79rc1       -> 2.79.0-rc1
            r"(?P<ma>\d+)\.(?P<mi>\d+)(?P<pre>\D[^\.\s]*)?",  #                                  <major>.<minor><patch?>                2.79          -> 2.79.0       | 2.79b -> 2.79.0-b
        ),
    )
)
initial_cleaner = re.compile(r"(?!blender-)\d.*(?=-linux|-windows)")


@cache
def parse_blender_ver(s: str, search=False) -> Version:
    """
    Converts Blender's different styles of versioning to a semver Version.
    Assumes s is either a semantic version or a blender style version. Otherwise things might get messy
    Versions ending with 'a' and 'b' will have a patch of 1 and 2.


    Arguments:
        s -- a blender version.

    Returns:
        Version
    """
    try:
        return Version.parse(s)
    except ValueError as e:
        m = initial_cleaner.search(s)
        if m is not None:
            s = m.group()
            try:
                return Version.parse(s)
            except ValueError:
                pass

        major = 0
        minor = 0
        patch = 0
        prerelease = None

        try:
            g = None
            if search:
                for matcher in matchers:
                    if (m := matcher.search(s)) is not None:
                        g = m
                        break
            else:
                for matcher in matchers:
                    if (m := matcher.match(s)) is not None:
                        g = m
                        break
            assert g is not None
        except (StopIteration, AssertionError):
            """No matcher gave any valid version"""
            raise ValueError("No valid version found") from e

        major = int(g.group("ma"))
        minor = int(g.group("mi"))
        if "pa" in g.groupdict():
            patch = int(g.group("pa"))
        if "pre" in g.groupdict() and g.group("pre") is not None:
            prerelease = g.group("pre").casefold().strip("- ")
            if prerelease.strip().lower() == "lts":
                prerelease = None

        return Version(major=major, minor=minor, patch=patch, prerelease=prerelease)
        # print(f"Parsed {s} to {v} using {matcher}")


oldver_cutoff = Version(2, 83, 0)


@dataclass
class BuildInfo:
    # Class variables
    file_version = "1.5"
    # https://www.blender.org/download/lts/
    lts_versions = tuple(f"{v.major}.{v.minor}" for v in lts_blender_version())

    # Build variables
    link: str
    subversion: str
    build_hash: str | None
    commit_time: datetime
    branch: str
    custom_name: str = ""
    is_favorite: bool = False
    custom_executable: str | None = None
    is_frozen: bool = False

    def __post_init__(self):
        if self.branch == "stable" and self.subversion.startswith(self.lts_versions):
            self.branch = "lts"

    def __eq__(self, other: BuildInfo):
        if (self is None) or (other is None):
            return False
        if (self.build_hash is not None) and (other.build_hash is not None):
            return self.build_hash == other.build_hash

        # Compare by semver major.minor.patch (ignore prerelease differences)
        # This allows "4.5.2" to match "4.5.2-window" for Bforartists builds
        try:
            self_ver = parse_blender_ver(self.subversion)
            other_ver = parse_blender_ver(other.subversion)
            return (
                self_ver.major == other_ver.major
                and self_ver.minor == other_ver.minor
                and self_ver.patch == other_ver.patch
            )
        except (ValueError, Exception):
            # Fall back to string comparison if parsing fails
            return self.subversion == other.subversion

    @property
    def semversion(self):
        return parse_blender_ver(self.subversion)

    @property
    def full_semversion(self):
        return BuildInfo.get_semver(self.subversion, self.branch, self.build_hash)

    @property
    def display_version(self):
        return self._display_version(self.semversion)

    @property
    def display_label(self):
        return self._display_label(self.branch, self.semversion, self.subversion)

    @property
    def bforartist_version_matcher(self):
        return bfa_version_matcher(self.semversion)

    @staticmethod
    @cache
    def _display_version(v: Version):
        if v < oldver_cutoff:
            pre = ""
            if v.prerelease:
                pre = v.prerelease
            return f"{v.major}.{v.minor}{pre}"
        return str(v.finalize_version())

    @staticmethod
    @cache
    def _display_label(branch: str, v: Version, subv: str):
        if branch == "lts":
            return "LTS"
        if branch in ("patch", "experimental", "daily"):
            b = v.prerelease
            if b is not None:
                return b.replace("-", " ").title()
            return subv.split("-", 1)[-1].title()

        if branch == "daily":
            b = v.prerelease
            if b is not None:
                b = branch.rsplit(".", 1)[0].title()
            else:
                b = subv.split("-", 1)[-1].title()
            return b
        if v.prerelease is not None:
            if v.prerelease.startswith("rc"):
                return f"Release Candidate {v.prerelease[2:]}"
            if sys.platform == "darwin" and branch == "stable":
                pre = v.prerelease
                if pre.startswith("macos"):
                    pre = pre.removeprefix("macos-")
                return f"{branch.title()} - {pre}"

        return branch.title()

    @staticmethod
    @cache
    def get_semver(subversion, *s: str):
        v = parse_blender_ver(subversion)
        if not s:
            return v
        prerelease = ""
        if v.prerelease:
            prerelease = f"{v.prerelease}+"
        prerelease += ".".join(s_ for s_ in s if s_)
        return v.replace(prerelease=prerelease)

    @classmethod
    def from_dict(cls, link: str, blinfo: dict):
        try:
            dt = datetime.fromisoformat(blinfo["commit_time"])
        except ValueError:  # old file version compatibility
            try:
                dt = datetime.strptime(blinfo["commit_time"], "%d-%b-%y-%H:%M").astimezone()
            except Exception:
                dt = dateparser.parse(blinfo["commit_time"]).astimezone()
        return cls(
            link,
            blinfo["subversion"],
            blinfo["build_hash"],
            dt,
            blinfo["branch"],
            blinfo["custom_name"],
            blinfo["is_favorite"],
            blinfo.get("custom_executable", ""),
            blinfo.get("is_frozen", False),
        )

    def to_dict(self):
        return {
            "file_version": self.__class__.file_version,
            "blinfo": [
                {
                    "branch": self.branch,
                    "subversion": self.subversion,
                    "build_hash": self.build_hash,
                    "commit_time": self.commit_time.isoformat(),
                    "custom_name": self.custom_name,
                    "is_favorite": self.is_favorite,
                    "custom_executable": self.custom_executable,
                    "is_frozen": self.is_frozen,
                }
            ],
        }

    def write_to(self, path: Path):
        data = self.to_dict()
        blinfo = path / ".blinfo"
        with blinfo.open("w", encoding="utf-8") as file:
            json.dump(data, file)
        return data

    def __lt__(self, other: BuildInfo):
        sv, osv = self.semversion.finalize_version(), other.semversion.finalize_version()
        if sv == osv:
            # sort by commit time if possible
            try:
                return self.commit_time < other.commit_time
            except Exception:  # Sometimes commit times are built without timezone information
                return self.full_semversion < other.full_semversion
        return sv < osv


def fill_blender_info(exe: Path, info: BuildInfo | None = None) -> tuple[datetime, str, str, str]:
    if not exe.exists():
        # List parent directory contents for debugging
        parent_contents = list(exe.parent.parent.iterdir()) if exe.parent.parent.exists() else []
        logger.error(
            f"Executable not found: {exe}\nParent directory contents: {[p.name for p in parent_contents[:10]]}"
        )
        raise FileNotFoundError(f"Executable not found: {exe}")

    version = _check_output([exe.as_posix(), "-v"]).decode("UTF-8")
    build_hash = ""
    subversion = ""
    custom_name = ""

    ctime = re.search("build commit time: (.*)", version)
    cdate = re.search("build commit date: (.*)", version)

    if info is None:
        if ctime is not None and cdate is not None:
            try:
                strptime = datetime.strptime(
                    f"{cdate[1].rstrip()} {ctime[1].rstrip()}",
                    "%Y-%m-%d %H:%M",
                ).astimezone()
            except Exception:
                strptime = dateparser.parse(f"{cdate[1].rstrip()} {ctime[1].rstrip()}")
        else:
            strptime = datetime.now().astimezone()
    else:
        strptime = info.commit_time

    if s := re.search("build hash: (.*)", version):
        build_hash = s[1].rstrip()

    if info is not None and info.subversion is not None:
        subversion = info.subversion
    elif s := re.search(r"(?:Blender|Bforartists) (.*)", version):
        subversion = s[1].rstrip()
    else:
        s = version.splitlines()[0].strip()
        custom_name, subversion = s.rsplit(" ", 1)

    return (
        strptime,
        build_hash,
        subversion,
        custom_name,
    )


def read_blender_version(
    path: Path,
    old_build_info: BuildInfo | None = None,
    archive_name=None,
) -> BuildInfo:
    # Track if we have valid old build info that we can reuse
    reuse_old_info = False
    corrected_exe_path = None

    if old_build_info is not None and old_build_info.custom_executable:
        exe_path = path / old_build_info.custom_executable
        # If the custom executable doesn't exist, fall back to auto-detection
        if not exe_path.exists():
            logger.warning(f"Custom executable not found: {exe_path}, falling back to auto-detection for {path.name}")
            # We still have the build info, just need to find the correct executable path
            reuse_old_info = True
        else:
            # Custom executable path is valid, use it
            corrected_exe_path = exe_path
            logger.debug(f"Using custom executable: {exe_path}")

    # Track if we found a non-standard path that should be saved as custom_executable
    found_nonstandard_path = False

    if corrected_exe_path is None:
        platform = get_platform()

        # Standard paths for different platforms
        blender_exe = {
            "Windows": "blender.exe",
            "Linux": "blender",
            "macOS": "Blender/Blender.app/Contents/MacOS/Blender",
        }.get(platform, "blender")

        bforartists_exe = {
            "Windows": "bforartists.exe",
            "Linux": "bforartists",
            "macOS": "Bforartists/Bforartists.app/Contents/MacOS/Bforartists",
        }.get(platform, "bforartists")

        # Auto-detect executable path
        # Priority: Bforartists (macOS DMG) > Bforartists (standard) > Blender (macOS DMG) > Blender (standard)
        bforartists_path = path / bforartists_exe

        if platform == "macOS" and (path / "Bforartists.app").is_dir():
            # macOS: DMG extraction places .app directly at root
            corrected_exe_path = path / "Bforartists.app" / "Contents/MacOS/Bforartists"
            found_nonstandard_path = True
        elif bforartists_path.is_file():
            # Standard Bforartists structure
            corrected_exe_path = bforartists_path
        elif platform == "macOS" and (path / "Blender.app").is_dir():
            # macOS: DMG extraction places .app directly at root
            corrected_exe_path = path / "Blender.app" / "Contents/MacOS/Blender"
            found_nonstandard_path = True
        else:
            # Standard Blender structure (fallback)
            corrected_exe_path = path / blender_exe

    # If we're reusing old info and found the correct executable, skip the slow version check
    if reuse_old_info and corrected_exe_path and corrected_exe_path.exists():
        logger.info(f"Reusing build info, updated executable path to: {corrected_exe_path.relative_to(path)}")
        commit_time = old_build_info.commit_time
        build_hash = old_build_info.build_hash
        subversion = old_build_info.subversion
        custom_name = old_build_info.custom_name
    else:
        # Need to read version info from the executable
        commit_time, build_hash, subversion, custom_name = fill_blender_info(corrected_exe_path, info=old_build_info)

    subfolder = path.parent.name

    name = archive_name or path.name
    branch = subfolder

    if subfolder == "custom":
        branch = name
    elif subfolder == "experimental":
        # Sensitive data! Requires proper folder naming!
        match = re.search(r"\+(.+?)\.", name)

        # Fix for naming conventions changes after 1.12.0 release
        if match is None:
            if old_build_info is not None:
                branch = old_build_info.branch
        else:
            branch = match.group(1)

    # Recover user defined favorites builds information
    is_favorite = False
    is_frozen = False
    custom_exe = None

    if old_build_info is not None:
        custom_name = old_build_info.custom_name
        is_favorite = old_build_info.is_favorite
        is_frozen = old_build_info.is_frozen

        # Update custom_exe with corrected path if we found a new one
        if reuse_old_info and corrected_exe_path:
            custom_exe = corrected_exe_path.relative_to(path).as_posix()
        elif found_nonstandard_path and corrected_exe_path:
            # Even with old_build_info, save the non-standard path if found
            custom_exe = corrected_exe_path.relative_to(path).as_posix()
        else:
            custom_exe = old_build_info.custom_executable
    elif found_nonstandard_path and corrected_exe_path:
        # For new builds with non-standard paths (DMG extraction format), save the detected executable path
        custom_exe = corrected_exe_path.relative_to(path).as_posix()

    return BuildInfo(
        path.as_posix(),
        subversion,
        build_hash,
        commit_time,
        branch,
        custom_name,
        is_favorite,
        custom_exe,
        is_frozen,
    )


@dataclass
class WriteBuildTask(Task):
    written = Signal()
    error = Signal()

    path: Path
    build_info: BuildInfo

    def run(self):
        try:
            self.build_info.write_to(self.path)
            self.written.emit()
        except Exception:
            self.error.emit()
            raise


def fill_build_info(
    path: Path,
    archive_name: str | None = None,
    info: BuildInfo | None = None,
    auto_write=True,
):
    blinfo = path / ".blinfo"

    # Check if build information is already present
    if blinfo.is_file():
        with blinfo.open(encoding="utf-8") as file:
            data = json.load(file)

        build_info = BuildInfo.from_dict(path.as_posix(), data["blinfo"][0])

        # Check if file version changed
        if ("file_version" not in data) or (data["file_version"] != BuildInfo.file_version):
            new_build_info = read_blender_version(
                path,
                build_info,
                archive_name,
            )
            new_build_info.write_to(path)
            return new_build_info
        return build_info

    # Generating new build information
    build_info = read_blender_version(
        path,
        old_build_info=info,
        archive_name=archive_name,
    )
    if auto_write:
        build_info.write_to(path)
    return build_info


@dataclass
class ReadBuildTask(Task):
    path: Path
    info: BuildInfo | None = None
    archive_name: str | None = None
    auto_write: bool = True

    finished = Signal(BuildInfo)
    failure = Signal(Exception)

    def run(self):
        try:
            build_info = fill_build_info(self.path, self.archive_name, self.info, self.auto_write)
            self.finished.emit(build_info)

        except Exception as e:
            self.failure.emit(e)
            raise

    def __str__(self):
        return f"Read build at {self.path}"


class LaunchMode: ...


@dataclass(frozen=True)
class LaunchWithBlendFile(LaunchMode):
    blendfile: Path


class LaunchOpenLast(LaunchMode): ...


def get_args(info: BuildInfo, exe=None, launch_mode: LaunchMode | None = None, linux_nohup=True) -> list[str] | str:
    platform = get_platform()
    library_folder = get_library_folder()
    blender_args = get_blender_startup_arguments()

    b3d_exe: Path
    args: str | list[str] = ""
    if platform == "Windows":
        if exe is not None:
            b3d_exe = library_folder / info.link / exe
            args = ["cmd", "/C", b3d_exe.as_posix()]
        else:
            cexe = info.custom_executable
            if cexe:
                b3d_exe = library_folder / info.link / cexe
            else:
                if (
                    get_launch_blender_no_console()
                    and (launcher := (library_folder / info.link / "blender-launcher.exe")).exists()
                ):
                    b3d_exe = launcher
                elif (bfa_exe := (library_folder / info.link / "bforartists.exe")).exists():
                    b3d_exe = bfa_exe
                else:
                    b3d_exe = library_folder / info.link / "blender.exe"

            # Check if the executable is a batch file and needs cmd /C
            if b3d_exe.suffix.lower() in (".bat", ".cmd"):
                if blender_args == "":
                    args = ["cmd", "/C", b3d_exe.as_posix()]
                else:
                    args = ["cmd", "/C", b3d_exe.as_posix(), *blender_args.split(" ")]
            else:
                if blender_args == "":
                    args = [b3d_exe.as_posix()]
                else:
                    args = [b3d_exe.as_posix(), *blender_args.split(" ")]

    elif platform == "Linux":
        bash_args = get_bash_arguments()

        if bash_args != "":
            bash_args += " "
        if linux_nohup:
            bash_args += "nohup"

        cexe = info.custom_executable
        if cexe:
            b3d_exe = library_folder / info.link / cexe
        elif (bfa_exe := (library_folder / info.link / "bforartists")).exists():
            b3d_exe = bfa_exe
        else:
            b3d_exe = library_folder / info.link / "blender"

        args = f'{bash_args} "{b3d_exe.as_posix()}" {blender_args}'

    elif platform == "macOS":
        # Auto-detect .app bundle path
        # Priority: Bforartists (DMG) > Blender (DMG) > Blender (standard)
        bforartists_app = Path(info.link) / "Bforartists.app"
        blender_app = Path(info.link) / "Blender.app"
        blender_standard_app = Path(info.link) / "Blender" / "Blender.app"

        if bforartists_app.is_dir():
            # macOS: Bforartists from DMG extraction
            b3d_exe = bforartists_app
        elif blender_app.is_dir():
            # macOS: Blender from DMG extraction
            b3d_exe = blender_app
        else:
            # macOS: Standard Blender structure (fallback)
            b3d_exe = blender_standard_app

        args = f"open -W -n {shlex.quote(b3d_exe.as_posix())} --args"

    if launch_mode is not None:
        if isinstance(launch_mode, LaunchWithBlendFile):
            if isinstance(args, list):
                args.append(launch_mode.blendfile.as_posix())
            else:
                args += f' "{launch_mode.blendfile.as_posix()}"'
        elif isinstance(launch_mode, LaunchOpenLast):
            if isinstance(args, list):
                args.append("--open-last")
            else:
                args += " --open-last"

    return args


def launch_build(info: BuildInfo, exe=None, launch_mode: LaunchMode | None = None):
    args = get_args(info, exe, launch_mode)
    logger.debug(f"Running build with args {args!s}")
    return _popen(args)


def bfa_version_matcher(bfa_blender_version: Version) -> Version | None:
    versions = read_blender_version_list()
    for i, version in enumerate(versions):
        if version.match(f"{bfa_blender_version.major}.{bfa_blender_version.minor}"):
            if i + 1 < len(versions) and i > 0:
                return versions[i - 1]
            else:
                return None
    return None
