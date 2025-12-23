from __future__ import annotations

import contextlib
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Sequence

from modules.blendfile_reader import read_blendfile_header
from modules.build_info import BuildInfo, LaunchMode, LaunchOpenLast, LaunchWithBlendFile, get_args
from modules.settings import get_favorite_path, get_version_specific_queries
from modules.version_matcher import BasicBuildInfo, BInfoMatcher, VersionSearchQuery
from threads.library_drawer import get_blender_builds

logger = logging.getLogger()


def cli_launch(
    file: Path | None = None,
    version_query: VersionSearchQuery | None = None,
    open_last: bool = False,
    blender_args: Sequence[str] = (),
) -> NoReturn:
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

    if version_query is None and file is None and (path := get_favorite_path()):
        logger.info("Launching quick launch build")
        for build in builds:
            if build.link == path:
                launch_mode = None
                if open_last:
                    launch_mode = LaunchOpenLast()

                args = get_args(build, launch_mode=launch_mode, linux_nohup=False)
                logger.info(f"Launching build with args: {args}")
                proc = subprocess.Popen(args, shell=True)
                sys.exit(proc.wait())

    basics = {BasicBuildInfo.from_buildinfo(b): b for b in builds}

    matcher = BInfoMatcher(tuple(basics.keys()))

    all_queries = get_version_specific_queries()

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

    launch_mode: LaunchMode | None = None
    if file is not None:
        launch_mode = LaunchWithBlendFile(file)
    if open_last:
        launch_mode = LaunchOpenLast()

    if len(matches) == 0:
        logger.exception(f"Could not find any matching builds for the query: '{query}'.")
        sys.exit(1)

    if len(matches) > 1:
        print(f"Found {len(matches)} matching builds:")
        for i, b in enumerate(matches):
            info = basics[b]
            print(f"- {i}: {Path(info.link).parent.stem}/{info.full_semversion}")

        # Enter which build to launch?
        while True:
            try:
                choice = int(input(f"\nEnter the number of the build you want to launch (0-{len(matches) - 1}): "))
                if 0 <= choice < len(matches):
                    break
            except ValueError:
                logger.exception("Invalid input!")

        build = matches[choice]
        build_info = basics[build]

    if len(matches) == 1:
        build = matches[0]
        build_info = basics[build]

    args = get_args(build_info, launch_mode=launch_mode, linux_nohup=False)
    if isinstance(args, list):
        args.extend(blender_args)
    else:
        args += f" {' '.join(blender_args)}"
    logger.info(f"Launching build: {build}")
    logger.info(f"With args: {args}")
    proc = subprocess.Popen(args, shell=True)

    sys.exit(proc.wait())
