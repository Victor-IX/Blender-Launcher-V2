from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import keyring
from keyring.errors import KeyringError, PasswordDeleteError
from modules._platform import get_config_file, get_config_path, get_cwd, get_platform, local_config, user_config
from modules.bl_api_manager import dropdown_blender_version
from modules.version_matcher import VersionSearchQuery
from PySide6.QtCore import QSettings
from semver import Version

logger = logging.getLogger(__name__)

EPOCH = datetime.fromtimestamp(0, tz=UTC)
ISO_EPOCH = EPOCH.isoformat()

# Keyring constants for secure token storage
KEYRING_SERVICE_NAME = "BlenderLauncher"
KEYRING_PROXY_HOST = "proxy/host"
KEYRING_PROXY_PORT = "proxy/port"
KEYRING_PROXY_USER = "proxy/user"
KEYRING_PROXY_PASSWORD = "proxy/password"
KEYRING_TOKEN_USERNAME = "github_token"

# TODO: Simplify this

tabs = {
    "Library": 0,
    "Downloads": 1,
    "Favorites": 2,
}

library_pages = {
    "Stable Releases": 0,
    "Daily Builds": 1,
    "Experimental Branches": 2,
    "Bforartists": 3,
    "UPBGE": 4,
    "UPBGE Weekly": 5,
    "Custom": 6,
}

downloads_pages = {
    "Stable Releases": 0,
    "Daily Builds": 1,
    "Experimental Branches": 2,
    "Bforartists": 3,
    "UPBGE": 4,
    "UPBGE Weekly": 5,
}

favorite_pages = {
    "Disable": 0,
    "Stable Releases": 1,
    "Daily Builds": 2,
    "Experimental Branches": 3,
}

library_subfolders = [
    "custom",
    "stable",
    "daily",
    "experimental",
    "bforartists",
    "template",
    "upbge-stable",
    "upbge-weekly",
]

proxy_types = {
    "None": 0,
    "HTTP": 1,
    "HTTPS": 2,
    "SOCKS4": 3,
    "SOCKS5": 4,
}

delete_action = {
    "Send to Trash": 0,
    "Delete Permanently": 1,
}

update_behavior = {
    "Major": 0,
    "Minor": 1,
    "Patch": 2,
}


def get_settings() -> QSettings:
    file = get_config_file()
    if not file.parent.is_dir():
        file.parent.mkdir(parents=True)

    return QSettings(get_config_file().as_posix(), QSettings.Format.IniFormat)


def get_actual_library_folder_no_fallback() -> Path | None:
    v = get_settings().value("library_folder")
    if v:
        return Path(v)
    return None


def get_actual_library_folder() -> Path:
    settings = get_settings()
    library_folder = settings.value("library_folder")
    if not is_library_folder_valid(library_folder):
        library_folder = get_cwd()

    return Path(library_folder)


def get_library_folder() -> Path:
    library_folder = get_actual_library_folder()

    if not library_folder.is_absolute():
        library_folder = get_cwd() / library_folder

    return library_folder.resolve()


def is_library_folder_valid(library_folder=None) -> bool:
    if library_folder is None:
        library_folder = get_settings().value("library_folder")

    if library_folder is not None:
        path = Path(library_folder)
        if not path.is_absolute():
            path = get_cwd() / path

        if path.exists():
            try:
                (path / ".temp").mkdir(parents=True, exist_ok=True)
            except PermissionError:
                return False

            return True

    return False


def set_library_folder(new_library_folder: str) -> bool:
    settings = get_settings()

    if is_library_folder_valid(new_library_folder) is True:
        settings.setValue("library_folder", new_library_folder)
        create_library_folders(new_library_folder)
        return True

    return False


def create_library_folders(library_folder):
    path = Path(library_folder)
    if not path.is_absolute():
        path = get_cwd() / path

    for subfolder in library_subfolders:
        (path / subfolder).mkdir(parents=True, exist_ok=True)


def get_favorite_path() -> str | None:
    return get_settings().value("Internal/favorite_path")  # type: ignore


def set_favorite_path(path):
    get_settings().setValue("Internal/favorite_path", path)


def get_dont_show_resource_warning() -> bool:
    return get_settings().value("Internal/dont_show_resource_err_again", type=bool, defaultValue=False)  # type: ignore


def set_dont_show_resource_warning(b: bool = True):
    get_settings().setValue("Internal/dont_show_resource_err_again", b)


def get_last_time_checked_utc() -> datetime:
    v: str = get_settings().value("Internal/last_time_checked_utc", defaultValue=ISO_EPOCH)  # type: ignore
    return datetime.fromisoformat(v)


def set_last_time_checked_utc(dt: datetime):
    get_settings().setValue("Internal/last_time_checked_utc", dt.isoformat())


def get_launch_when_system_starts() -> bool:
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
        path = sys.executable
        _, count, _ = winreg.QueryInfoKey(key)

        for i in range(count):
            with contextlib.suppress(OSError):
                name, value, _ = winreg.EnumValue(key, i)

                if name == "Blender Launcher":
                    return value == path

        key.Close()
    return False


def set_launch_when_system_starts(is_checked):
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )

        if is_checked:
            path = sys.executable
            winreg.SetValueEx(key, "Blender Launcher", 0, winreg.REG_SZ, path)
        else:
            with contextlib.suppress(Exception):
                winreg.DeleteValue(key, "Blender Launcher")

        key.Close()


def get_launch_minimized_to_tray() -> bool:
    return get_settings().value("launch_minimized_to_tray", type=bool)  # type: ignore


def set_launch_minimized_to_tray(is_checked):
    get_settings().setValue("launch_minimized_to_tray", is_checked)


def get_dpi_scale_factor() -> float:
    return get_settings().value("dpi_scale_factor", defaultValue=1.0, type=float)  # type: ignore


def set_dpi_scale_factor(val: float):
    get_settings().setValue("dpi_scale_factor", val)


def get_sync_library_and_downloads_pages() -> bool:
    return get_settings().value("sync_library_and_downloads_pages", defaultValue=True, type=bool)  # type: ignore


def set_sync_library_and_downloads_pages(is_checked):
    get_settings().setValue("sync_library_and_downloads_pages", is_checked)


def get_default_library_page() -> int:
    return get_settings().value("default_library_page", defaultValue=0, type=int)  # type: ignore


def set_default_library_page(page):
    get_settings().setValue("default_library_page", library_pages[page])


def get_mark_as_favorite() -> int:
    return get_settings().value("mark_as_favorite", defaultValue=0, type=int)  # type: ignore


def set_mark_as_favorite(page):
    get_settings().setValue("mark_as_favorite", favorite_pages[page])


def get_default_downloads_page() -> int:
    return get_settings().value("default_downloads_page", defaultValue=0, type=int)  # type: ignore


def set_default_downloads_page(page):
    get_settings().setValue("default_downloads_page", downloads_pages[page])


def get_default_tab() -> int:
    return get_settings().value("default_tab", defaultValue=0, type=int)  # type: ignore


def set_default_tab(tab):
    get_settings().setValue("default_tab", tabs[tab])


def get_list_sorting_type(list_name) -> int:
    return get_settings().value(f"Internal/{list_name}_sorting_type", defaultValue=1, type=int)  # type: ignore


def set_list_sorting_type(list_name, sorting_type):
    get_settings().setValue(f"Internal/{list_name}_sorting_type", sorting_type.value)


def get_enable_new_builds_notifications() -> bool:
    return get_settings().value("enable_new_builds_notifications", defaultValue=True, type=bool)  # type: ignore


def set_enable_new_builds_notifications(is_checked):
    get_settings().setValue("enable_new_builds_notifications", is_checked)


def get_enable_download_notifications() -> bool:
    return get_settings().value("enable_download_notifications", defaultValue=True, type=bool)  # type: ignore


def set_enable_download_notifications(is_checked):
    get_settings().setValue("enable_download_notifications", is_checked)


def get_blender_startup_arguments() -> str:
    args: str = get_settings().value("blender_startup_arguments", defaultValue="", type=str)  # type: ignore
    return args.strip()


def set_blender_startup_arguments(args):
    get_settings().setValue("blender_startup_arguments", args.strip())


def get_bash_arguments() -> str:
    args: str = get_settings().value("bash_arguments", defaultValue="", type=str)  # type: ignore
    return args.strip()


def set_bash_arguments(args):
    get_settings().setValue("bash_arguments", args.strip())


def get_show_update_button() -> bool:
    return get_settings().value("show_update_button", defaultValue=True, type=bool)  # type: ignore


def set_show_update_button(is_checked):
    get_settings().setValue("show_update_button", is_checked)


def get_use_advanced_update_button() -> bool:
    return get_settings().value("use_advanced_update_button", defaultValue=False, type=bool)  # type: ignore


def set_use_advanced_update_button(is_checked):
    get_settings().setValue("use_advanced_update_button", is_checked)


def set_show_stable_update_button(is_checked):
    get_settings().setValue("show_stable_update_button", is_checked)


def get_show_stable_update_button() -> bool:
    return get_settings().value("show_stable_update_button", defaultValue=True, type=bool)  # type: ignore


def set_show_daily_update_button(is_checked):
    get_settings().setValue("show_daily_update_button", is_checked)


def get_show_daily_update_button() -> bool:
    return get_settings().value("show_daily_update_button", defaultValue=True, type=bool)  # type: ignore


def set_show_experimental_update_button(is_checked):
    get_settings().setValue("show_experimental_update_button", is_checked)


def get_show_experimental_update_button() -> bool:
    return get_settings().value("show_experimental_update_button", defaultValue=True, type=bool)  # type: ignore


def set_show_bfa_update_button(is_checked):
    get_settings().setValue("show_bfa_update_button", is_checked)


def get_show_bfa_update_button() -> bool:
    return get_settings().value("show_bfa_update_button", defaultValue=True, type=bool)  # type: ignore


def get_update_behavior() -> int:
    return get_settings().value("update_behavior", defaultValue=2, type=int)  # type: ignore


def set_update_behavior(behavior):
    get_settings().setValue("update_behavior", update_behavior[behavior])


def get_stable_update_behavior() -> int:
    return get_settings().value("stable_update_behavior", defaultValue=2, type=int)  # type: ignore


def set_stable_update_behavior(behavior):
    get_settings().setValue("stable_update_behavior", update_behavior[behavior])


def get_daily_update_behavior() -> int:
    return get_settings().value("daily_update_behavior", defaultValue=2, type=int)  # type: ignore


def set_daily_update_behavior(behavior):
    get_settings().setValue("daily_update_behavior", update_behavior[behavior])


def get_experimental_update_behavior() -> int:
    return get_settings().value("experimental_update_behavior", defaultValue=2, type=int)  # type: ignore


def set_experimental_update_behavior(behavior):
    get_settings().setValue("experimental_update_behavior", update_behavior[behavior])


def get_bfa_update_behavior() -> int:
    return get_settings().value("bfa_update_behavior", defaultValue=2, type=int)  # type: ignore


def set_bfa_update_behavior(behavior):
    get_settings().setValue("bfa_update_behavior", update_behavior[behavior])


def set_show_upbge_stable_update_button(is_checked):
    get_settings().setValue("show_upbge_stable_update_button", is_checked)


def get_show_upbge_stable_update_button() -> bool:
    return get_settings().value("show_upbge_stable_update_button", defaultValue=True, type=bool)  # type: ignore


def get_upbge_stable_update_behavior() -> int:
    return get_settings().value("upbge_stable_update_behavior", defaultValue=2, type=int)  # type: ignore


def set_upbge_stable_update_behavior(behavior):
    get_settings().setValue("upbge_stable_update_behavior", update_behavior[behavior])


def set_show_upbge_weekly_update_button(is_checked):
    get_settings().setValue("show_upbge_weekly_update_button", is_checked)


def get_show_upbge_weekly_update_button() -> bool:
    return get_settings().value("show_upbge_weekly_update_button", defaultValue=True, type=bool)  # type: ignore


def get_upbge_weekly_update_behavior() -> int:
    return get_settings().value("upbge_weekly_update_behavior", defaultValue=2, type=int)  # type: ignore


def set_upbge_weekly_update_behavior(behavior):
    get_settings().setValue("upbge_weekly_update_behavior", update_behavior[behavior])


def get_install_template() -> bool:
    return get_settings().value("install_template", type=bool)  # type: ignore


def set_install_template(is_checked):
    get_settings().setValue("install_template", is_checked)


def get_show_tray_icon() -> bool:
    return get_settings().value("show_tray_icon", defaultValue=False, type=bool)  # type: ignore


def set_show_tray_icon(is_checked):
    get_settings().setValue("show_tray_icon", is_checked)


def get_tray_icon_notified() -> bool:
    return get_settings().value("Internal/tray_icon_notified", defaultValue=False, type=bool)  # type: ignore


def set_tray_icon_notified(b=True):
    get_settings().setValue("Internal/tray_icon_notified", b)


def get_launch_blender_no_console() -> bool:
    return get_settings().value("launch_blender_no_console", defaultValue=True, type=bool)  # type: ignore


def set_launch_blender_no_console(is_checked):
    get_settings().setValue("launch_blender_no_console", is_checked)


def get_quick_launch_key_seq() -> str:
    s: str = get_settings().value("quick_launch_key_seq", defaultValue="alt+f11", type=str)  # type: ignore
    return s.strip()


def set_quick_launch_key_seq(key_seq):
    get_settings().setValue("quick_launch_key_seq", key_seq.strip())


def get_enable_quick_launch_key_seq() -> bool:
    return get_settings().value("enable_quick_launch_key_seq", defaultValue=False, type=bool)  # type: ignore


def set_enable_quick_launch_key_seq(is_checked):
    get_settings().setValue("enable_quick_launch_key_seq", is_checked)


def get_proxy_type() -> int:
    return get_settings().value("proxy/type", defaultValue=0, type=int)  # type: ignore


def set_proxy_type(proxy_type):
    get_settings().setValue("proxy/type", proxy_types[proxy_type])


def get_proxy_host() -> str:
    return _get_keyring_value(KEYRING_PROXY_HOST, default="255.255.255.255")


def set_proxy_host(args):
    return _set_keyring_value(KEYRING_PROXY_HOST, args.strip())


def get_proxy_port() -> str:
    return _get_keyring_value(KEYRING_PROXY_PORT, default="9999")


def set_proxy_port(args):
    return _set_keyring_value(KEYRING_PROXY_PORT, args.strip())


def get_proxy_user() -> str:
    return _get_keyring_value(KEYRING_PROXY_USER)


def set_proxy_user(args):
    return _set_keyring_value(KEYRING_PROXY_USER, args.strip())


def get_proxy_password() -> str:
    return _get_keyring_value(KEYRING_PROXY_PASSWORD)


def set_proxy_password(args):
    return _set_keyring_value(KEYRING_PROXY_PASSWORD, args.strip())


def get_use_custom_tls_certificates() -> bool:
    return get_settings().value("use_custom_tls_certificates", defaultValue=True, type=bool)  # type: ignore


def set_use_custom_tls_certificates(is_checked):
    get_settings().setValue("use_custom_tls_certificates", is_checked)


def get_user_id() -> str:
    id_: str = get_settings().value("user_id", type=str)  # type: ignore
    user_id = id_.strip()
    if not user_id:
        user_id = str(uuid.uuid4())
        set_user_id(user_id)
    return user_id


def set_user_id(user_id):
    get_settings().setValue("user_id", user_id.strip())


def get_github_token() -> str:
    return _get_keyring_value(KEYRING_TOKEN_USERNAME)


def set_github_token(token: str) -> bool:
    return _set_keyring_value(KEYRING_TOKEN_USERNAME, token.strip())


def _get_keyring_value(key: str, default="") -> str:
    """
    Get a value from secure system keyring.
    Falls back to legacy QSettings storage if keyring fails.
    """
    try:
        token = keyring.get_password(KEYRING_SERVICE_NAME, key)
        if token:
            return token.strip()
    except KeyringError as e:
        logger.warning(f"Failed to access keyring for key {key}: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error accessing keyring: {e}")

    # Fallback: check legacy QSettings storage and migrate if possible
    legacy_value = get_settings().value(key)
    if legacy_value and legacy_value.strip():
        legacy_value = legacy_value.strip()
        try:
            keyring.set_password(KEYRING_SERVICE_NAME, key, legacy_value)
            get_settings().remove(key)
            logger.info(f"Migrated {key} from legacy storage to secure keyring")
        except Exception as e:
            logger.warning(f"Failed to migrate {key} to keyring: {e}")
        return legacy_value

    return default


def _set_keyring_value(key: str, val: str) -> bool:
    """
    Stores key/value pair in secure system keyring.
    Falls back to QSettings if keyring is unavailable.


    Returns:
        bool: True if stored in keyring successfully, False if fell back to QSettings use to trigger user warning.
    """
    settings = get_settings()
    try:
        if val:
            # Store in secure keyring
            keyring.set_password(KEYRING_SERVICE_NAME, key, val)
            logger.debug(f"{key} stored in secure keyring")
            # Remove from QSettings if it exists there
            if settings.contains(key):
                settings.remove(key)
        else:
            # Delete token from keyring if empty
            try:
                keyring.delete_password(KEYRING_SERVICE_NAME, key)
                logger.debug(f"{key} removed from secure keyring")
            except PasswordDeleteError:
                pass  # Given key didn't exist, this is fine
        return True
    except KeyringError as e:
        logger.warning(f"Keyring unavailable, falling back to QSettings: {e}")
        # Fallback to QSettings
        settings.setValue(key, val)
    except Exception as e:
        logger.error(f"Failed to store hidden settings: {e}")
        # Fallback to QSettings
        settings.setValue(key, val)

    return False


# Blender Build Tab
def get_check_for_new_builds_automatically() -> bool:
    settings = get_settings()

    if settings.contains("check_for_new_builds_automatically"):
        return settings.value("check_for_new_builds_automatically", type=bool)  # type: ignore
    return False


def set_check_for_new_builds_automatically(is_checked):
    get_settings().setValue("check_for_new_builds_automatically", is_checked)


def get_new_builds_check_frequency() -> int:
    """Time in hours"""

    settings = get_settings()

    if settings.contains("new_builds_check_frequency"):
        frequency: int = settings.value("new_builds_check_frequency", defaultValue=12, type=int)  # type: ignore

        # Clamp value to minimum to prevent user bypass
        if frequency < 6:
            frequency = 6
            set_new_builds_check_frequency(6)

        return frequency
    return 12


def set_new_builds_check_frequency(frequency):
    if frequency < 6:
        frequency = 6
    get_settings().setValue("new_builds_check_frequency", frequency)


def get_check_for_new_builds_on_startup() -> bool:
    return get_settings().value("buildcheck_on_startup", defaultValue=True, type=bool)  # type: ignore


def set_check_for_new_builds_on_startup(b: bool):
    get_settings().setValue("buildcheck_on_startup", b)


def get_minimum_blender_stable_version() -> str:
    value: str = get_settings().value("minimum_blender_stable_version", defaultValue="3.0", type=str)  # type: ignore
    # value can never be None
    if value == "None":
        return "3.0"

    # backwards compatibility for indexes
    # (This is not recommended because it relies on the dropdown blender versions to be static)
    with contextlib.suppress(ValueError, IndexError):
        if "." not in value:
            return list(dropdown_blender_version())[int(value)]
    return value


def set_minimum_blender_stable_version(blender_minimum_version: str):
    get_settings().setValue("minimum_blender_stable_version", blender_minimum_version)


def get_scrape_stable_builds() -> bool:
    return get_settings().value("scrape_stable_builds", defaultValue=True, type=bool)  # type: ignore


def set_scrape_stable_builds(b: bool):
    get_settings().setValue("scrape_stable_builds", b)


# For backcompat -- keep for a few versions
def get_scrape_automated_builds() -> bool:
    return get_settings().value("scrape_automated_builds", defaultValue=True, type=bool)  # type: ignore


def get_scrape_daily_builds() -> bool:
    s = get_settings()
    if not s.contains("scrape_daily_builds") and s.contains("scrape_automated_builds"):
        return get_scrape_automated_builds()

    return s.value("scrape_daily_builds", defaultValue=True, type=bool)  # type: ignore


def set_scrape_daily_builds(b: bool):
    get_settings().setValue("scrape_daily_builds", b)


def get_scrape_experimental_builds() -> bool:
    s = get_settings()
    if not s.contains("scrape_experimental_builds") and s.contains("scrape_automated_builds"):
        return get_scrape_automated_builds()

    return s.value("scrape_experimental_builds", defaultValue=True, type=bool)  # type: ignore


def set_scrape_experimental_builds(b: bool):
    get_settings().setValue("scrape_experimental_builds", b)


def get_scrape_bfa_builds() -> bool:
    return get_settings().value("scrape_bfa_builds", defaultValue=True, type=bool)  # type: ignore


def set_scrape_bfa_builds(b: bool):
    get_settings().setValue("scrape_bfa_builds", b)


def get_scrape_upbge_builds() -> bool:
    return get_settings().value("scrape_upbge_builds", defaultValue=True, type=bool)  # type: ignore


def set_scrape_upbge_builds(b: bool):
    get_settings().setValue("scrape_upbge_builds", b)


def get_scrape_upbge_weekly_builds() -> bool:
    return get_settings().value("scrape_upbge_weekly_builds", defaultValue=False, type=bool)  # type: ignore


def set_scrape_upbge_weekly_builds(b: bool):
    get_settings().setValue("scrape_upbge_weekly_builds", b)


def get_show_stable_builds() -> bool:
    return get_settings().value("show_stable_builds", defaultValue=True, type=bool)  # type: ignore


def set_show_stable_builds(b: bool):
    get_settings().setValue("show_stable_builds", b)


def get_show_daily_builds() -> bool:
    return get_settings().value("show_daily_builds", defaultValue=True, type=bool)  # type: ignore


def set_show_daily_builds(b: bool):
    get_settings().setValue("show_daily_builds", b)


def get_show_experimental_and_patch_builds() -> bool:
    return get_settings().value("show_experimental_and_patch_builds", defaultValue=True, type=bool)  # type: ignore


def set_show_experimental_and_patch_builds(b: bool):
    get_settings().setValue("show_experimental_and_patch_builds", b)


def get_show_bfa_builds() -> bool:
    return get_settings().value("show_bfa_builds", defaultValue=True, type=bool)  # type: ignore


def set_show_bfa_builds(b: bool):
    get_settings().setValue("show_bfa_builds", b)


def get_show_upbge_builds() -> bool:
    return get_settings().value("show_upbge_builds", defaultValue=True, type=bool)  # type: ignore


def set_show_upbge_builds(b: bool):
    get_settings().setValue("show_upbge_builds", b)


def get_show_upbge_weekly_builds() -> bool:
    return get_settings().value("show_upbge_weekly_builds", defaultValue=False, type=bool)  # type: ignore


def set_show_upbge_weekly_builds(b: bool):
    get_settings().setValue("show_upbge_weekly_builds", b)


def get_show_daily_archive_builds() -> bool:
    return get_settings().value("show_daily_archive_builds", defaultValue=False, type=bool)  # type: ignore


def set_show_daily_archive_builds(b: bool):
    get_settings().setValue("show_daily_archive_builds", b)


def get_show_experimental_archive_builds() -> bool:
    return get_settings().value("show_experimental_archive_builds", defaultValue=False, type=bool)  # type: ignore


def set_show_experimental_archive_builds(b: bool):
    get_settings().setValue("show_experimental_archive_builds", b)


def get_show_patch_archive_builds() -> bool:
    return get_settings().value("show_patch_archive_builds", defaultValue=False, type=bool)  # type: ignore


def set_show_patch_archive_builds(b: bool):
    get_settings().setValue("show_patch_archive_builds", b)


def get_make_error_popup() -> bool:
    return get_settings().value("error_popup", defaultValue=True, type=bool)  # type: ignore


def set_make_error_notifications(v: bool):
    get_settings().setValue("error_popup", v)


def get_default_worker_thread_count() -> int:
    cpu_count = os.cpu_count()
    if cpu_count is None:  # why can os.cpu_count() return None
        return 4

    return round(max(cpu_count * 3 / 4, 1))


def get_worker_thread_count() -> int:
    v: int = get_settings().value("worker_thread_count", type=int)  # type: ignore
    if v == 0:
        return get_default_worker_thread_count()

    return v


def set_worker_thread_count(v: int):
    get_settings().setValue("worker_thread_count", v)


def get_use_pre_release_builds() -> bool:
    return get_settings().value("use_pre_release_builds", defaultValue=False, type=bool)  # type: ignore


def set_use_pre_release_builds(b: bool):
    get_settings().setValue("use_pre_release_builds", b)


def get_use_system_titlebar() -> bool:
    return get_settings().value("use_system_title_bar", defaultValue=False, type=bool)  # type: ignore


def set_use_system_titlebar(b: bool):
    get_settings().setValue("use_system_title_bar", b)


def get_version_specific_queries() -> dict[Version, VersionSearchQuery]:
    dct: str = get_settings().value("version_specific_queries", defaultValue="{}", type=str)  # type: ignore
    if dct is None:  # <-- unreachable?
        return {}
    return {Version.parse(k): VersionSearchQuery.parse(v) for k, v in json.loads(dct).items()}


def set_version_specific_queries(dct: dict[Version, VersionSearchQuery]):
    v = {str(k): str(v) for k, v in dct.items()}
    j = json.dumps(v)
    get_settings().setValue("version_specific_queries", j)


def get_launch_timer_duration() -> int:
    return get_settings().value("launch_timer", defaultValue=3, type=int)  # type: ignore


def set_launch_timer_duration(duration: int):
    """Sets the launch timer duration, in seconds"""
    get_settings().setValue("launch_timer", duration)


def get_first_time_setup_seen() -> bool:
    return get_settings().value("first_time_setup_seen", defaultValue=False, type=bool)  # type: ignore


def set_first_time_setup_seen(b: bool):
    get_settings().setValue("first_time_setup_seen", b)


def get_default_delete_action() -> int:
    return get_settings().value("default_delete_action", defaultValue=0, type=int)  # type: ignore


def set_default_delete_action(action):
    get_settings().setValue("default_delete_action", delete_action[action])


def migrate_config(force=False):
    config_path = Path(get_config_path())
    old_config = local_config()
    new_config = user_config()
    if (old_config.is_file() and not new_config.is_file()) or force:
        if not config_path.is_dir():
            config_path.mkdir()
        shutil.move(old_config.resolve(), new_config.resolve())


def get_column_widths() -> list[int]:
    """Get saved column widths (global, shared across all lists)."""

    # Use global key - all lists share the same column widths
    value: str = get_settings().value("Internal/global_column_widths", defaultValue="[73, 434, 124]", type=str)  # type: ignore
    try:
        widths: list[int] = json.loads(value)
        if isinstance(widths, list) and len(widths) == 3:
            return widths
    except json.JSONDecodeError:
        pass
    return [73, 434, 124]


def set_column_widths(widths: list[int]):
    """Save column widths (global, shared across all lists)."""

    # Use global key - all lists share the same column widths
    get_settings().setValue("Internal/global_column_widths", json.dumps(widths))


def get_purge_temp_on_startup() -> bool:
    return get_settings().value("purge_temp_on_startup", defaultValue=True, type=bool)  # type: ignore


def set_purge_temp_on_startup(is_checked: bool):
    get_settings().setValue("purge_temp_on_startup", is_checked)


def purge_temp_folder():
    """Purge all files in the temp folder."""
    temp_folder = Path(get_library_folder()) / ".temp"
    if temp_folder.exists() and temp_folder.is_dir():
        try:
            for item in temp_folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            return True
        except Exception:
            return False
    return True


def get_auto_register_winget() -> bool:
    return get_settings().value("auto_register_winget", defaultValue=True, type=bool)  # type: ignore


def set_auto_register_winget(is_enabled: bool):
    get_settings().setValue("auto_register_winget", is_enabled)
