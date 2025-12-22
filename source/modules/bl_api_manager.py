import sys
import json
import logging

from functools import lru_cache
from pathlib import Path
from semver import Version

from modules._platform import get_config_path, get_platform

logger = logging.getLogger()

CONFIG_PATH = Path(get_config_path())
BL_API_PATH = CONFIG_PATH / "Blender Launcher API.json"
STABLE_BUILD_PATH = CONFIG_PATH / "stable_builds.json"

if getattr(sys, "frozen", False):
    INTERNAL_BL_API_PATH = Path(getattr(sys, "_MEIPASS", "")) / "files/blender_launcher_api.json"
    INTERNAL_STABLE_BUILD_PATH = (
        Path(getattr(sys, "_MEIPASS", "")) / f"files/stable_builds_api_{get_platform().lower()}.json"
    )
else:
    INTERNAL_BL_API_PATH = Path("source/resources/api/blender_launcher_api.json").resolve()
    INTERNAL_STABLE_BUILD_PATH = Path(f"source/resources/api/stable_builds_api_{get_platform().lower()}.json").resolve()


def update_stable_builds_cache(data: dict | None) -> None:
    try:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        if data is None and INTERNAL_STABLE_BUILD_PATH.is_file():
            logger.debug("No data provided; trying to read stable builds from internal file.")
            data = load_json(INTERNAL_STABLE_BUILD_PATH)
        if not data:
            logger.critical("Failed to acquire build cache API data.")
            return

        if STABLE_BUILD_PATH.is_file():
            logger.debug("Reading build cache version from existing file.")
            try:
                current_data = load_json(STABLE_BUILD_PATH)
                version_current = float(current_data.get("api_file_version", -1))
                version_new = float(data.get("api_file_version", 0))
                if version_current >= version_new:
                    logger.info(
                        f"Current {version_current} build cache version is newer or equal to the new data ({version_new}). Not updating."
                    )
                    return
                else:
                    logger.info(
                        f"Current {version_current} build cache version is older than the new data ({version_new}). Updating."
                    )
            except Exception as e:
                logger.exception("Failed to compare build cache versions from existing file. Overwriting file.")

        with STABLE_BUILD_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
            logger.info(f"Created or updated stable builds cache file in {STABLE_BUILD_PATH}")
    except OSError as e:
        logger.exception(f"Failed to write stable builds cache: {e}")
    except Exception as e:
        logger.exception(f"Failed to update stable builds cache: {e}")


@lru_cache(maxsize=1)
def read_bl_api() -> dict:
    data = {}
    if BL_API_PATH.exists():
        data = load_json(BL_API_PATH)
        if not data:
            logger.info(f"Failed to load external API file from {BL_API_PATH}. Falling back to internal API file.")
            data = load_json(INTERNAL_BL_API_PATH)
    else:
        logger.info(f"API file not found in {BL_API_PATH}. Using internal API file.")
        data = load_json(INTERNAL_BL_API_PATH)
    return data


def load_json(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.exception(f"Invalid or broken JSON in {path}: {e}")
    except Exception as e:
        logger.exception(f"Error reading {path}: {e}")
    return {}


def update_local_api_files(data: dict) -> None:
    try:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        with BL_API_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
            logger.info(f"Updated API file in {BL_API_PATH}")
        read_bl_api.cache_clear()
    except OSError as e:
        logger.exception(f"Failed to write API file: {e}")
    except Exception as e:
        logger.exception(f"Failed to update API file: {e}")


def read_blender_version_list() -> list[Version]:
    return [
        Version.parse(version, optional_minor_and_patch=True)
        for version in read_bl_api().get("blender_versions", {}).keys()
    ]


def lts_blender_version() -> list[Version]:
    versions = read_bl_api().get("blender_versions", {})
    return [Version.parse(version, optional_minor_and_patch=True) for version, lts in versions.items() if lts == "LTS"]


def dropdown_blender_version() -> dict[str, int]:
    """Ex:
    {
        "4.0": 0,
        "3.6": 1,
        "3.5": 2,
        "3.4": 3
    }
    """
    versions = tuple(f"{v.major}.{v.minor}" for v in read_blender_version_list())
    return {version: i for i, version in enumerate(versions)}
