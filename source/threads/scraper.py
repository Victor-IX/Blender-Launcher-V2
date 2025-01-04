from __future__ import annotations

import base64
import contextlib
import json
import logging
import re
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import dateparser
import distro
from bs4 import BeautifulSoup, SoupStrainer
from modules._platform import (
    bfa_cache_path,
    get_architecture,
    get_platform,
    stable_cache_path,
)
from modules.bl_api_manager import (
    dropdown_blender_version,
    lts_blender_version,
    update_local_api_files,
    update_stable_builds_cache,
)
from modules.build_info import BuildInfo, parse_blender_ver
from modules.scraper_cache import ScraperCache
from modules.settings import (
    get_minimum_blender_stable_version,
    get_scrape_automated_builds,
    get_scrape_bfa_builds,
    get_scrape_stable_builds,
    get_show_daily_archive_builds,
    get_show_experimental_archive_builds,
    get_show_patch_archive_builds,
    get_use_pre_release_builds,
)
from PySide6.QtCore import QThread, Signal
from semver import Version
from webdav4.client import Client

if TYPE_CHECKING:
    from modules.connection_manager import ConnectionManager

logger = logging.getLogger()

# NC: NextCloud
BFA_NC_BASE_URL = "https://cloud.bforartists.de"
BFA_NC_HTTPS_URL = f"{BFA_NC_BASE_URL}/index.php/s"
# https://archive.ph/esTuX#accessing-public-shares-over-webdav
BFA_NC_WEBDAV_URL = f"{BFA_NC_BASE_URL}/public.php/webdav"
BFA_NC_WEBDAV_SHARE_TOKEN = "JxCjbyt2fFcHjy4"


def get_bfa_nc_https_download_url(webdav_file_path: PurePosixPath):
    return f"{BFA_NC_HTTPS_URL}/{BFA_NC_WEBDAV_SHARE_TOKEN}/download?path=/{webdav_file_path.parent}&files={webdav_file_path.name}"


def get_release_tag(connection_manager: ConnectionManager) -> str | None:
    if get_use_pre_release_builds():
        url = "https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/releases"
        latest_tag = get_tag(connection_manager, url, pre_release=True)
    else:
        url = "https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest"
        latest_tag = get_tag(connection_manager, url)

    logger.info(f"Latest release tag: {latest_tag}")

    return latest_tag


def get_tag(
    connection_manager: ConnectionManager,
    url: str,
    pre_release=False,
) -> str | None:
    r = connection_manager.request("GET", url)

    if r is None:
        return None

    if pre_release:
        try:
            parsed_data = json.loads(r.data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pre-release tag JSON data: {e}")
            return None

        platform = get_platform()

        if platform.lower() == "linux":
            for key in (
                distro.id().title(),
                distro.like().title(),
                distro.id(),
                distro.like(),
            ):
                if "ubuntu" in key.lower():
                    platform = "Ubuntu"
                    break

        platform_valid_tags = (
            release["tag_name"]
            for release in parsed_data
            for asset in release["assets"]
            if asset["name"].endswith(".zip") and platform.lower() in asset["name"].lower()
        )
        pre_release_tags = (release.lstrip("v") for release in platform_valid_tags)

        valid_pre_release_tags = [tag for tag in pre_release_tags if Version.is_valid(tag)]

        if valid_pre_release_tags:
            tag = max(valid_pre_release_tags, key=Version.parse)
            return f"v{tag}"

        r.release_conn()
        r.close()

        return None

    else:
        url = r.geturl()
        tag = url.rsplit("/", 1)[-1]

        r.release_conn()
        r.close()

        return tag


def get_api_data(connection_manager: ConnectionManager, file: str) -> str | None:
    base_fmt = "https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/contents/source/resources/api/{}.json"
    url = base_fmt.format(file)
    logger.debug(f"Start fetching API data from: {url}")
    r = connection_manager.request("GET", url)

    if r is None:
        logger.error(f"Failed to fetch data from: {url}.")
        return None

    try:
        data = json.loads(r.data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {file} API JSON data: {e}")
        return None

    file_content = data.get("content")
    file_content_encoding = data.get("encoding")

    if file_content_encoding == "base64" and file_content:
        try:
            file_content = base64.b64decode(file_content).decode("utf-8")
            json_data = json.loads(file_content)
            logger.info(f"API data form {file} have been loaded successfully")
            return json_data
        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode or parse JSON data: {e}")
            return None
    else:
        logger.error(f"Failed to load API data from {file} or unsupported encoding.")
        return None


def get_latest_patch_note(connection_manager: ConnectionManager, latest_tag) -> str | None:
    if latest_tag is None:
        logger.error("Failed to get the latest release tag.")
        return None

    url = f"https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/releases/tags/{latest_tag}"
    r = connection_manager.request("GET", url)

    if r is None:
        logger.error(f"Failed to fetch release notes for tag: {latest_tag}")
        return None

    try:
        release_data = json.loads(r.data)
        patch_note = release_data.get("body", "No patch notes available.")
        logger.info(f"Latest patch note found")
        return patch_note
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse release notes JSON data: {e}")
        return None


class Scraper(QThread):
    links = Signal(BuildInfo)
    new_bl_version = Signal(str, str)
    error = Signal()
    stable_error = Signal(str)

    def __init__(self, parent, man: ConnectionManager, build_cache=False):
        QThread.__init__(self)
        self.parent = parent
        self.manager = man
        self.build_cache = build_cache

        self.platform = get_platform()
        self.architecture = get_architecture()

        self.cache_path = stable_cache_path()
        self.bfa_cache_path = bfa_cache_path()

        self.cache = ScraperCache.from_file_or_default(self.cache_path)
        self.bfa_cache = ScraperCache.from_file_or_default(self.bfa_cache_path)

        self.json_platform = {
            "Windows": "windows",
            "Linux": "linux",
            "macOS": "darwin",
        }.get(self.platform, self.platform)

        self.regex_filter()

        self.hash = re.compile(r"\w{12}")
        self.subversion = re.compile(r"-\d\.[a-zA-Z0-9.]+-")

        self.scrape_stable = get_scrape_stable_builds()
        self.scrape_automated = get_scrape_automated_builds()
        self.scrape_bfa = get_scrape_bfa_builds()

        self._latest_tag_cache = None

    def regex_filter(self):
        if self.platform == "Windows":
            regex_filter = r"blender-.+win.+64.+zip$"
            bfa_regex_filter = r"Bforartists-.+Windows.+zip"
        elif self.platform == "macOS":
            regex_filter = r"blender-.+(macOS|darwin).+dmg$"
            bfa_regex_filter = r"Bforartists-.+dmg$"
        else:
            regex_filter = r"blender-.+lin.+64.+tar+(?!.*sha256).*"
            bfa_regex_filter = r"Bforartists-.+tar.xz$"

        self.b3d_link = re.compile(regex_filter, re.IGNORECASE)
        self.bfa_package_file_name_regex = re.compile(bfa_regex_filter, re.IGNORECASE)

    def run(self):
        self.get_api_data_manager()
        self.get_download_links()
        self.get_new_release_manager()

    def get_cached_release_tag(self) -> str | None:
        if self._latest_tag_cache is None:
            self._latest_tag_cache = get_release_tag(self.manager)
        return self._latest_tag_cache

    def get_new_release_manager(self):
        assert self.manager.manager is not None
        latest_tag = self.get_cached_release_tag()

        if latest_tag is not None:
            patch_note = get_latest_patch_note(self.manager, latest_tag)
            self.new_bl_version.emit(latest_tag, patch_note)
        self.manager.manager.clear()

    def get_api_data_manager(self):
        assert self.manager.manager is not None

        bl_api_data = get_api_data(self.manager, "blender_launcher_api")
        blender_version_api_data = get_api_data(self.manager, f"stable_builds_api_{self.platform.lower()}")

        if bl_api_data is not None:
            update_local_api_files(bl_api_data)
            lts_blender_version()
            dropdown_blender_version()

        update_stable_builds_cache(blender_version_api_data)

        self.cache = ScraperCache.from_file_or_default(self.cache_path)
        self.manager.manager.clear()

    def get_download_links(self):
        scrapers = []
        if self.scrape_stable:
            scrapers.append(self.scrap_stable_releases())
        if self.scrape_automated:
            scrapers.append(self.scrape_automated_releases())
        if self.scrape_bfa:
            scrapers.append(self.scrape_bfa_releases())
        if self.build_cache:
            platforms = ["Windows", "linux", "macOS"]
            for platform in platforms:
                scrapers.append(self.scrap_stable_releases(platform))

        for build in chain(*scrapers):
            # Filter out builds that don't match the current platform for Windows
            if self.platform.lower() == "windows":
                if self.architecture == "arm64" and "arm64" in build.link:
                    self.links.emit(build)
                    continue
                elif self.architecture == "amd64" and (
                    ("x64" in build.link or "windows64" in build.link)
                    or "amd64" in build.link
                    or "bforartists" in build.link.lower()
                ):
                    self.links.emit(build)
                    continue
                else:
                    logger.debug(f"Skipping {build.link} as it doesn't match the current platform")
            else:
                self.links.emit(build)
                continue

    def scrape_automated_releases(self):
        base_fmt = "https://builder.blender.org/download/{}/?format=json&v=1"

        branch_mapping = {
            "daily": get_show_daily_archive_builds,
            "experimental": get_show_experimental_archive_builds,
            "patch": get_show_patch_archive_builds,
        }

        branches = tuple(
            f"{branch}/archive" if check_archive() else branch for branch, check_archive in branch_mapping.items()
        )

        for branch_type in branches:
            url = base_fmt.format(branch_type)
            r = self.manager.request("GET", url)

            if r is None:
                continue

            data = json.loads(r.data)
            architecture_specific_build = False

            # Remove /archive from branch name
            if "/archive" in branch_type:
                branch_type = branch_type.replace("/archive", "")

            for build in data:
                if (
                    build["platform"] == self.json_platform
                    and build["architecture"].lower() == self.architecture
                    and self.b3d_link.match(build["file_name"])
                ):
                    architecture_specific_build = True
                    yield self.new_build_from_dict(build, branch_type, architecture_specific_build)

            if not architecture_specific_build:
                logger.warning(
                    f"No builds found for {branch_type} build on {self.platform} architecture {self.architecture}"
                )

                for build in data:
                    if build["platform"] == self.json_platform and self.b3d_link.match(build["file_name"]):
                        yield self.new_build_from_dict(build, branch_type, architecture_specific_build)

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

    def scrap_download_links(self, url, branch_type, _limit=None):
        r = self.manager.request("GET", url)

        if r is None:
            return

        content = r.data

        soup_stainer = SoupStrainer("a", href=True)
        soup = BeautifulSoup(content, "lxml", parse_only=soup_stainer)

        # Update regex filter with corresponding platform
        if self.build_cache:
            self.regex_filter()

        for tag in soup.find_all(limit=_limit, href=self.b3d_link):
            build_info = self.new_blender_build(tag, url, branch_type)

            if build_info is not None:
                yield build_info

        r.release_conn()
        r.close()

    def new_blender_build(self, tag, url, branch_type):
        link = urljoin(url, tag["href"]).rstrip("/")
        r = self.manager.request("HEAD", link)

        if r is None:
            return None

        if r.status != 200:
            return None

        info = r.headers
        build_hash: str | None = None
        stem = Path(link).stem
        match = re.findall(self.hash, stem)

        if match:
            build_hash = match[-1].replace("-", "")

        subversion = parse_blender_ver(stem, search=True)
        branch = branch_type
        if branch_type != "stable":
            build_var = ""
            tag = tag.find_next("span", class_="build-var")

            # For some reason tag can be None on macOS
            if tag is not None:
                build_var = tag.get_text()

            if self.platform == "macOS":
                if "arm64" in link:
                    build_var = "{} │ {}".format(build_var, "Arm")
                elif "x86_64" in link:
                    build_var = "{} │ {}".format(build_var, "Intel")

            if branch_type == "experimental":
                branch = build_var
            elif branch_type == "daily":
                branch = "daily"
                subversion = subversion.replace(prerelease=build_var)

        if self.platform == "macOS":
            # Skip Intel builds on Apple Silicon
            if self.architecture == "arm64" and "arm64" not in link:
                return None

            # Skip Apple Silicon builds on Intel
            if self.architecture == "x64" and "x64" not in link:
                return None

        commit_time = dateparser.parse(info["last-modified"]).astimezone()
        r.release_conn()
        r.close()
        return BuildInfo(link, str(subversion), build_hash, commit_time, branch)

    def scrap_stable_releases(self, platform=None):
        # Use for cache building only
        if self.build_cache and platform is not None:
            self.platform = platform
            self.cache_path = stable_cache_path().with_name(f"stable_builds_{platform}.json")
            self.cache = ScraperCache.from_file_or_default(self.cache_path)
            print(f"Scraping stable releases for {platform}")

        url = "https://download.blender.org/release/"
        r = self.manager.request("GET", url)

        if r is None:
            return

        content = r.data
        soup = BeautifulSoup(content, "lxml")

        b3d_link = re.compile(r"Blender(\d+\.\d+)")

        releases = soup.find_all(href=b3d_link)
        if not any(releases):
            logger.info(f"Failed to gather stable releases for {platform}")
            logger.info(content)
            self.stable_error.emit(
                f"No releases were scraped from the site for {platform}!<br>check -debug logs for more details."
            )
            return

        minimum_version_str = get_minimum_blender_stable_version()
        if minimum_version_str == "None":
            minimum_smver_version = Version(2, 48, 0)
        else:
            major, minor = minimum_version_str.split(".")
            minimum_smver_version = Version(int(major), int(minor), 0)

        if self.build_cache:
            minimum_smver_version = Version(2, 48, 0)

        cache_modified = False
        for release in releases:
            href = release["href"]
            match = re.search(b3d_link, href)
            if match is None:
                continue

            ver = parse_blender_ver(match.group(1))
            if ver >= minimum_smver_version:
                # Check modified dates of folders, if available
                date_sibling = release.find_next_sibling(string=True)
                if date_sibling:
                    date_str = " ".join(date_sibling.strip().split()[:2])
                    with contextlib.suppress(ValueError):
                        modified_date = dateparser.parse(date_str)
                        if ver not in self.cache:
                            logger.debug(f"Creating new folder for version {ver}")
                            folder = self.cache.new_build(ver)
                        else:
                            folder = self.cache[ver]

                        if folder.modified_date != modified_date:
                            folder.assets.clear()
                            for build in self.scrap_download_links(urljoin(url, href), "stable"):
                                folder.assets.append(build)
                                yield build

                            logger.debug(
                                f"Caching {href}: {modified_date} (previous was {folder.modified_date}) for platform {platform}"
                            )
                            folder.modified_date = modified_date
                            cache_modified = True
                        else:
                            logger.debug(f"Skipping {href}: {modified_date} for platform {platform}")

                        builds = self.cache[ver].assets

                        if not self.build_cache:
                            yield from builds
                        continue

                yield from self.scrap_download_links(urljoin(url, href), "stable")

        if cache_modified:
            cache_path = self.cache_path
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(self.cache.to_dict(), f)
                logging.debug(f"Saved cache to {cache_path}")

        r.release_conn()
        r.close()

    def scrape_bfa_releases(self):
        client = Client(BFA_NC_WEBDAV_URL, auth=(BFA_NC_WEBDAV_SHARE_TOKEN, ""))
        cache_modified = False
        for entry in client.ls("", detail=True, allow_listing_resource=True):
            if isinstance(entry, str):
                continue
            if entry["type"] != "directory":
                continue
            try:
                semver = Version.parse(entry["name"].split()[-1])
            except ValueError:
                continue

            # check if the cache needs to be updated
            modified_date: datetime = entry["modified"]
            if semver not in self.bfa_cache:
                folder = self.bfa_cache.new_build(semver)
            else:
                folder = self.bfa_cache[semver]

            if folder.modified_date < modified_date:
                for release in self.scrape_bfa_release(client, entry["name"], semver):
                    folder.assets.append(release)
                    yield release

                folder.modified_date = modified_date
                cache_modified = True
            else:
                logger.debug(f"Skipping {entry['name']}: {modified_date}")
                yield from folder.assets

        if cache_modified:
            with self.bfa_cache_path.open("w", encoding="utf-8") as f:
                json.dump(self.bfa_cache.to_dict(), f)
                logging.debug(f"Saved cache to {self.bfa_cache_path}")

    def scrape_bfa_release(self, client: Client, folder: str, semver: Version):
        for entry in client.ls(folder, detail=True, allow_listing_resource=True):
            if isinstance(entry, str):
                continue
            path = entry["name"]
            ppath = PurePosixPath(path)
            if self.bfa_package_file_name_regex.match(ppath.name) is None:
                continue
            commit_time = entry["modified"]
            if not isinstance(commit_time, datetime):
                continue

            exe_name = {
                "Windows": "bforartists.exe",
                "Linux": "bforartists",
                "macOS": "Bforartists/Bforartists.app/Contents/MacOS/Bforartists",
            }.get(get_platform(), "bforartists")
            yield BuildInfo(
                get_bfa_nc_https_download_url(ppath),
                str(semver),
                None,
                commit_time.astimezone(),
                "bforartists",
                custom_executable=exe_name,
            )
