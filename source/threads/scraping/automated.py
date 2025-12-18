from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Generator

from modules._platform import (
    get_architecture,
    get_platform,
)
from modules.build_info import BuildInfo, parse_blender_ver

from source.threads.scraping.base import BuildScraper, regex_filter

if TYPE_CHECKING:
    from modules.connection_manager import ConnectionManager

logger = logging.getLogger()


class ScraperAutomated(BuildScraper):
    def __init__(self, man: ConnectionManager, branch: str):
        super().__init__()
        self.manager = man
        self.branch = branch

        self.architecture = get_architecture()
        self.platform = get_platform()
        self.json_platform = {
            "Windows": "windows",
            "Linux": "linux",
            "macOS": "darwin",
        }.get(self.platform, self.platform)

    def scrape(self) -> Generator[BuildInfo, None, None]:
        base_fmt = "https://builder.blender.org/download/{}/?format=json&v=1"

        url = base_fmt.format(self.branch)
        r = self.manager.request("GET", url)

        if r is None:
            return

        data = json.loads(r.data)
        architecture_specific_build = False

        branch = self.branch
        # Remove /archive from branch name
        if "/archive" in branch:
            branch = branch.replace("/archive", "")

        link_filter = regex_filter()

        for build in data:
            if (
                build["platform"] == self.json_platform
                and build["architecture"].lower() == self.architecture
                and link_filter.match(build["file_name"])
            ):
                architecture_specific_build = True
                yield self.new_build_from_dict(build, branch, architecture_specific_build)

        if not architecture_specific_build:
            logger.warning(f"No builds found for {branch} build on {self.platform} architecture {self.architecture}")

            for build in data:
                if build["platform"] == self.json_platform and link_filter.match(build["file_name"]):
                    yield self.new_build_from_dict(build, branch, architecture_specific_build)

    def new_build_from_dict(self, build, branch_type, architecture_specific_build):
        dt = datetime.fromtimestamp(build["file_mtime"], tz=timezone.utc)

        subversion = parse_blender_ver(build["version"])
        build_var = ""
        if build["patch"] is not None and branch_type != "daily":
            build_var = build["patch"]
        if build["release_cycle"] is not None and branch_type == "daily":
            build_var = build["release_cycle"]
        if build["branch"] and branch_type == "experimental":
            build_var = build["branch"]

        if "architecture" in build and not architecture_specific_build:
            if build["architecture"] == "amd64":
                build["architecture"] = "x86_64"
            build_var += " | " + build["architecture"]

        if build_var:
            subversion = subversion.replace(prerelease=build_var)

        return BuildInfo(
            build["url"],
            str(subversion),
            build["hash"],
            dt,
            branch_type,
        )
