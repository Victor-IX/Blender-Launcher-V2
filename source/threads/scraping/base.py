from __future__ import annotations

import re
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING

from modules.platform_utils import get_platform

if TYPE_CHECKING:
    from collections.abc import Generator

    from modules.build_info import BuildInfo


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
