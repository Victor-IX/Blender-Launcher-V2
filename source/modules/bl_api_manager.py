import json
import logging
import sys
from functools import lru_cache
from pathlib import Path

from modules._platform import get_config_path, get_cwd, get_platform

logger = logging.getLogger()

config_path = Path(get_config_path())
bl_api_path = config_path / "Blender Launcher API.json"
stable_build_path = config_path / "stable_builds.json"

if getattr(sys, "frozen", False):
    internal_bl_api_path = Path(sys._MEIPASS) / "files/blender_launcher_api.json"  # noqa: SLF001
    internal_stable_build_path = Path(sys._MEIPASS) / f"files/stable_builds_api_{get_platform().lower()}.json"  # noqa: SLF001
else:
    internal_bl_api_path = Path("source/resources/api/blender_launcher_api.json").resolve()
    internal_stable_build_path = Path(f"source/resources/api/stable_builds_api_{get_platform().lower()}.json").resolve()


def update_local_api_files(data):
    try:
        config_path.mkdir(parents=True, exist_ok=True)
        with open(bl_api_path, "w") as f:
            json.dump(data, f, indent=4)
            logger.info(f"Updated API file in {bl_api_path}")
        read_bl_api.cache_clear()
    except OSError as e:
        logger.error(f"Failed to write API file: {e}")


def update_stable_builds_cache(data):
    try:
        config_path.mkdir(parents=True, exist_ok=True)
        if data is None and internal_stable_build_path.is_file():
            logger.debug("Trying to read stable builds from internal file.")
            with open(internal_stable_build_path) as f:
                data = json.load(f)
        if data is None:
            logger.critical("Fail to get build cache API data.")
            return

        if stable_build_path.is_file():
            logger.debug("Reading build cache version from existing file.")
            try:
                with open(stable_build_path) as f:
                    current_data = json.load(f)
                    if current_data["api_file_version"] == data["api_file_version"]:
                        logger.info("Current build cache version is up to date.")
                        return
                    elif current_data["api_file_version"] > data["api_file_version"]:
                        logger.info("Current build cache version is newer than the one provided. Not updating.")
                        return
                    else:
                        logger.info("Current build cache version is older than the one provided. Updating.")
            except KeyError:
                logger.error("Failed to read build cache version from existing file. Overwriting file.")

        current_data = data

        with open(stable_build_path, "w") as f:
            json.dump(current_data, f, indent=1)
            logger.info(f"Create or update stable builds cache file in {stable_build_path}")
    except OSError as e:
        logger.error(f"Failed to write stable builds cache: {e}")


@lru_cache(maxsize=1)
def read_bl_api() -> dict:
    api = bl_api_path if bl_api_path.exists() else internal_bl_api_path
    if api == internal_bl_api_path:
        logger.error(f"API file not found in {bl_api_path}. Using internal API file.")

    with open(api) as f:
        return json.load(f)


def read_blender_version_list() -> dict[str, str]:
    return read_bl_api().get("blender_versions", {})


def lts_blender_version():
    return tuple(version for version, lts in read_blender_version_list().items() if lts == "LTS")


def dropdown_blender_version() -> dict[str, int]:
    """Ex:

    {
        "4.0": 0,
        "3.6": 1,
        "3.5": 2,
        "3.4": 3
    }
    """
    return {key: index for index, key in enumerate(read_blender_version_list().keys())}
