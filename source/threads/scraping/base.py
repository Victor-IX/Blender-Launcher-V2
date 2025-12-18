from __future__ import annotations

import base64
import contextlib
import json
import logging
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import lru_cache
from itertools import chain
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Generator
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
    get_scrape_bfa_builds,
    get_scrape_daily_builds,
    get_scrape_experimental_builds,
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


class BuildScraper(ABC):
    @abstractmethod
    def scrape(self) -> Generator[BuildInfo, None, None]: ...


@lru_cache(maxsize=4)
def regex_filter(platform: str | None = None) -> re.Pattern:
    if platform is None:
        platform = get_platform()
    if platform == "Windows":
        regex_filter = r"blender-.+win.+64.+zip$"
    elif platform == "macOS":
        regex_filter = r"blender-.+(macOS|darwin).+dmg$"
    else:
        regex_filter = r"blender-.+lin.+64.+tar+(?!.*sha256).*"

    return re.compile(regex_filter, re.IGNORECASE)
