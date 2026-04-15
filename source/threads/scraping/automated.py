import json
import logging
import re
from collections.abc import Generator
from datetime import UTC, datetime

from modules.build_info import BuildInfo, parse_blender_ver
from modules.connection_manager import ConnectionManager
from modules.platform_utils import get_architecture, get_platform
from modules.settings import get_fetch_pr_names_during_scrape, get_prepend_prnum_on_prlabel
from threads.scraping.base import BuildScraper, regex_filter
from threads.scraping.pr_labels import PrLabelFetcher

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
        dt = datetime.fromtimestamp(build["file_mtime"], tz=UTC)

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


PR_MATCH: re.Pattern[str] = re.compile(r"PR(\d+)")


class ScraperPatch(ScraperAutomated):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.label_fetcher = PrLabelFetcher(self.manager)

    def scrape(self) -> Generator[BuildInfo, None, None]:
        if not get_fetch_pr_names_during_scrape():
            yield from super().scrape()
            return

        prepend_prnum = get_prepend_prnum_on_prlabel()

        unlabeled: list[tuple[int, BuildInfo]] = []
        for binfo in super().scrape():
            v = binfo.semversion
            if v.prerelease is None or (m := PR_MATCH.match(v.prerelease)) is None:
                yield binfo
                continue

            n = int(m.group(1))
            name = self.label_fetcher.get_cached(n)
            if name is None:
                unlabeled.append((n, binfo))
            else:
                binfo.custom_name = f"{n}: {name}" if prepend_prnum else name
                yield binfo

        if unlabeled:
            self.label_fetcher.cache_latest_pages()

        for n, build in unlabeled:
            name = self.label_fetcher.get(n)
            if name is not None:
                build.custom_name = f"{n}: {name}" if prepend_prnum else name
            yield build

        self.label_fetcher.save()
