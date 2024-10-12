from __future__ import annotations

import contextlib
import json
import logging
import subprocess
from pathlib import Path

from modules import prefs_info
from modules.blendfile_reader import read_blendfile_header
from modules.build_info import (
    BuildInfo,
    get_args,
)
from modules.build_info import LaunchArgs as LA
from modules.settings import get_favorite_path, get_library_folder, get_version_specific_queries
from modules.version_matcher import BasicBuildInfo, BInfoMatcher, VersionSearchQuery
from threads.library_drawer import get_blender_builds

from ._platform import overlay_environment

logger = logging.getLogger()


def select_build(
    builds: list[BuildInfo],
    file: Path | None = None,
    version_query: VersionSearchQuery | None = None,
) -> BuildInfo | None:
    if version_query is None and file is None and (fav_path := get_favorite_path()):
        logger.info("Searching for quick launch build")
        for build in builds:
            if build.link == fav_path:
                return build

    basics = {BasicBuildInfo.from_buildinfo(b): b for b in builds}
    matcher = BInfoMatcher(tuple(basics.keys()))

    all_queries = get_version_specific_queries()

    query = None
    if version_query is not None:
        query = version_query

    if file is not None and file.exists():
        logger.info("Reading file header...")
        header = read_blendfile_header(file)

        logger.debug(f"File header: {header}")

        if header is not None:
            v = header.version
            if v in all_queries:
                query = all_queries[v]
            else:
                query = VersionSearchQuery(v.major, v.minor, "^")

    if query is None:
        logger.warning("Could not read file header and no version was provided! defaulting to ^.^.^")
        query = VersionSearchQuery("^", "^", "^")

    matches = matcher.match(query)

    if len(matches) > 1:
        print(f"Found {len(matches)} matching builds:")
        for i, b in enumerate(matches):
            info = basics[b]
            print(f"- {i}: {Path(info.link).parent.stem}/{info.full_semversion}")

        # Enter which build to launch?
        while True:
            try:
                choice = int(input(f"\nEnter the number of the build you want to launch (0-{len(matches)-1}): "))
                if 0 <= choice < len(matches):
                    break
            except ValueError:
                print("Invalid input!")

        return basics[matches[choice]]

    if len(matches) == 1:
        return basics[matches[0]]

    return None


def cli_launch(
    file: Path | None = None,
    version_query: VersionSearchQuery | None = None,
    pref_mode: str | None = None,
    open_last: bool = False,
) -> int:
    # Search for builds
    logger.info("Searching for all builds")
    builds: list[BuildInfo] = []
    for build, _ in get_blender_builds(folders=("stable", "daily", "experimental", "custom")):
        if (blinfo := build / ".blinfo").exists():
            with blinfo.open("r", encoding="utf-8") as f:
                blinfo = json.load(f)
            with contextlib.suppress(Exception):
                info = BuildInfo.from_dict(str(build), blinfo["blinfo"][0])
                builds.append(info)

    builds.sort(reverse=True)

    build_info = select_build(builds, file, version_query)

    if build_info is None:
        logger.info("No build was chosen from matches")
        return 1

    launch_mode: LA.LaunchMode | None = None
    if file is not None:
        launch_mode = LA.LaunchWithBlendFile(file)
    if open_last:
        launch_mode = LA.LaunchOpenLast()

    env = None

    if pref_mode is not None and pref_mode != "default" or (pref_mode := build_info.target_preferences) is not None:
        logging.info("Searching for configs...")
        prefs_folder = get_library_folder() / "config"
        for p in (p_ for p_ in prefs_folder.iterdir() if p_.is_dir()):
            cfg = prefs_info.read_prefs(p)
            if cfg.name == pref_mode:
                logging.info(f"Found environment: {cfg}")
                env = cfg.get_env(build_info.semversion)
                break

    args = get_args(build_info, launch_mode=launch_mode, linux_nohup=False)
    logger.info(f"Launching build: {build}")
    logger.info(f"With args: {args}")
    logger.info(f"With env {env}")
    e = overlay_environment(env)
    proc = subprocess.Popen(args, env=e, shell=True)

    return proc.wait()
