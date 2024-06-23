from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from semver import Version


@dataclass
class ConfigInfo:
    file_version = "1.0"

    directory: Path
    target_version: Version
    name: str

    # TODO: Finish this __eq__ method

    def __eq__(self, other: ConfigInfo):
        if (self is None) or (other is None):  # what
            return False

        return self.directory == other.directory and self.target_version == other.target_version

    def get_env(self) -> dict[str, str]:
        return {
            "BLENDER_USER_CONFIG": str(self.directory / "config"),
            "BLENDER_USER_SCRIPTS": str(self.directory / "scripts"),
            "BLENDER_USER_DATAFILES": str(self.directory / "datafiles"),
        }

    @classmethod
    def from_dict(cls, confinfo: dict):
        return cls(
            Path(confinfo["directory"]),
            Version.parse(confinfo["target_version"]),
            confinfo["name"],
        )

    def to_dict(self):
        return {
            "file_version": self.__class__.file_version,
            "confinfo": [
                {
                    "directory": str(self.directory),
                    "target_version": str(self.target_version),
                    "name": self.name,
                }
            ],
        }

    def write_to(self, path: Path):
        data = self.to_dict()
        blinfo = path / ".confinfo"
        with blinfo.open("w", encoding="utf-8") as file:
            json.dump(data, file)
        return data
