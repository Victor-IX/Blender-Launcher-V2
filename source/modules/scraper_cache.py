from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from modules.build_info import BuildInfo
from modules.settings import EPOCH
from semver import Version

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger()

# Template of stable response for reference:
STABLE_TEMPLATE = """
<html>
<head><title>Index of /release/</title></head>
<body>
<h1>Index of /release/</h1><hr/><pre><a href="../">../</a>
<a href="Blender1.0/">Blender1.0/</a>                                        11-Jul-2020 07:17                   -
<a href="Blender4.1/">Blender4.1/</a>                                        26-Mar-2024 10:57                   -
</pre><hr/></body>
</html>
"""

# Template of release folder for reference:
STABLE_FOLDER_TEMPLATE = """<a href="../">../</a><a href="blender-4.0.0-linux-x64.tar.xz">blender-4.0.0-linux-x64.tar.xz</a><a href="blender-4.0.0-macos-arm64.dmg">blender-4.0.0-macos-arm64.dmg</a><a href="blender-4.0.0-macos-x64.dmg">blender-4.0.0-macos-x64.dmg</a><a href="blender-4.0.0-windows-x64.msi">blender-4.0.0-windows-x64.msi</a><a href="blender-4.0.0-windows-x64.msix">blender-4.0.0-windows-x64.msix</a><a href="blender-4.0.0-windows-x64.zip">blender-4.0.0-windows-x64.zip</a><a href="blender-4.0.0.md5">blender-4.0.0.md5</a><a href="blender-4.0.0.sha256">blender-4.0.0.sha256</a><a href="blender-4.0.1-linux-x64.tar.xz">blender-4.0.1-linux-x64.tar.xz</a><a href="blender-4.0.1-macos-arm64.dmg">blender-4.0.1-macos-arm64.dmg</a><a href="blender-4.0.1-macos-x64.dmg">blender-4.0.1-macos-x64.dmg</a><a href="blender-4.0.1-windows-x64.msi">blender-4.0.1-windows-x64.msi</a><a href="blender-4.0.1-windows-x64.msix">blender-4.0.1-windows-x64.msix</a><a href="blender-4.0.1-windows-x64.zip">blender-4.0.1-windows-x64.zip</a><a href="blender-4.0.1.md5">blender-4.0.1.md5</a><a href="blender-4.0.1.sha256">blender-4.0.1.sha256</a><a href="blender-4.0.2-linux-x64.tar.xz">blender-4.0.2-linux-x64.tar.xz</a><a href="blender-4.0.2-macos-arm64.dmg">blender-4.0.2-macos-arm64.dmg</a><a href="blender-4.0.2-macos-x64.dmg">blender-4.0.2-macos-x64.dmg</a><a href="blender-4.0.2-windows-x64.msi">blender-4.0.2-windows-x64.msi</a><a href="blender-4.0.2-windows-x64.msix">blender-4.0.2-windows-x64.msix</a><a href="blender-4.0.2-windows-x64.zip">blender-4.0.2-windows-x64.zip</a><a href="blender-4.0.2.md5">blender-4.0.2.md5</a><a href="blender-4.0.2.sha256">blender-4.0.2.sha256</a>
<a href="../">../</a><a href="blender-4.1.0-linux-x64.tar.xz">blender-4.1.0-linux-x64.tar.xz</a><a href="blender-4.1.0-macos-arm64.dmg">blender-4.1.0-macos-arm64.dmg</a><a href="blender-4.1.0-macos-x64.dmg">blender-4.1.0-macos-x64.dmg</a><a href="blender-4.1.0-windows-x64.msi">blender-4.1.0-windows-x64.msi</a><a href="blender-4.1.0-windows-x64.msix">blender-4.1.0-windows-x64.msix</a><a href="blender-4.1.0-windows-x64.zip">blender-4.1.0-windows-x64.zip</a><a href="blender-4.1.0.md5">blender-4.1.0.md5</a><a href="blender-4.1.0.sha256">blender-4.1.0.sha256</a>
"""


@dataclass
class StableFolder:
    assets: list[BuildInfo]
    modified_date: datetime

    @classmethod
    def from_dict(cls, dct: dict):
        return cls(
            assets=[BuildInfo.from_dict(link, build["blinfo"][0]) for link, build in dct["assets"]],
            modified_date=datetime.fromisoformat(dct["modified_date"]),
        )

    def to_dict(self):
        return {
            "assets": [(build.link, build.to_dict()) for build in self.assets],
            "modified_date": self.modified_date.isoformat(),
        }


@dataclass
class ScraperCache:
    folders: dict[Version, StableFolder] = field(default_factory=dict)

    def __contains__(self, ver: Version) -> bool:
        return ver in self.folders

    def __getitem__(self, ver: Version) -> StableFolder:
        return self.folders[ver]

    def new_build(self, ver: Version, dt: datetime | None = None):
        folder = StableFolder([], dt if dt is not None else EPOCH)
        self.folders[ver] = folder
        return folder

    @classmethod
    def try_from_file(cls, file: Path):
        """Tries to load a cache from a file. If it fails, returns None"""
        try:
            with file.open(encoding="utf-8") as f:
                cache = json.load(f)
                logger.debug(f"Loaded cache from {file!r}")
                return cls.from_dict(cache)
        except (json.decoder.JSONDecodeError, FileNotFoundError, OSError) as e:
            logger.exception(f"Failed to load cache {file}: {e}")
            return None

    @classmethod
    def from_file_or_default(cls, file: Path):
        """Tries to load a cache from a file. If it fails, returns an empty StableCache"""
        return c if (c := cls.try_from_file(file)) is not None else cls()

    @classmethod
    def from_dict(cls, dct: dict):
        return cls(
            folders={
                Version.parse(version): StableFolder.from_dict(value)
                for version, value in dct.get("folders", {}).items()
            },
        )

    def to_dict(self):
        return {"folders": {str(v): folder.to_dict() for v, folder in self.folders.items()}}
