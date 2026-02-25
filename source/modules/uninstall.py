from __future__ import annotations

import contextlib
import logging
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

import keyring
from keyring.errors import PasswordDeleteError

from modules.platform_utils import get_cache_path, get_config_path, local_config
from modules.settings import (
    KEYRING_PROXY_HOST,
    KEYRING_PROXY_PASSWORD,
    KEYRING_PROXY_PORT,
    KEYRING_PROXY_USER,
    KEYRING_SERVICE_NAME,
    KEYRING_TOKEN_USERNAME,
)
from modules.shortcut import get_default_program_shortcut_destination, unregister_windows_filetypes
from modules.winget_integration import unregister_from_winget

logger = logging.getLogger(__name__)


def perform_uninstall(quiet: bool = False) -> None:
    """Perform a full uninstall of Blender Launcher.

    Cleans up all application data, registry entries, shortcuts, keyring secrets,
    and optionally deletes the executable itself.

    Args:
        quiet: If True, skip any interactive confirmation prompts.
    """
    if sys.platform != "win32":
        logger.error("Uninstall command is only supported on Windows")
        sys.exit(1)

    if not quiet:
        answer = input("Are you sure you want to uninstall Blender Launcher? [y/N] ")
        if answer.lower() not in ("y", "yes"):
            logger.info("Uninstall cancelled by user")
            sys.exit(0)

    logger.info("Starting Blender Launcher uninstall...")

    _remove_startup_entry()
    _remove_file_associations()
    _remove_winget_registry()
    _remove_keyring_entries()
    _remove_start_menu_shortcut()
    _remove_config_and_cache()
    _remove_winget_package_dir()
    _schedule_self_deletion()

    logger.info("Uninstall complete")
    sys.exit(0)


def _remove_startup_entry() -> None:
    """Remove the 'Launch when system starts' registry entry."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, "Blender Launcher")
                logger.info("Removed startup registry entry")
    except Exception as e:
        logger.warning(f"Failed to remove startup entry: {e}")


def _remove_file_associations() -> None:
    """Remove .blend file association registry entries."""
    try:
        unregister_windows_filetypes()
        logger.info("Removed file associations")
    except Exception as e:
        logger.warning(f"Failed to remove file associations: {e}")


def _remove_winget_registry() -> None:
    """Remove the WinGet/ARP uninstall registry key."""
    try:
        unregister_from_winget()
        logger.info("Removed WinGet registry entry")
    except Exception as e:
        logger.warning(f"Failed to remove WinGet registry: {e}")


def _remove_keyring_entries() -> None:
    """Remove all secrets stored in the system keyring."""
    try:
        for key in (
            KEYRING_PROXY_HOST,
            KEYRING_PROXY_PORT,
            KEYRING_PROXY_USER,
            KEYRING_PROXY_PASSWORD,
            KEYRING_TOKEN_USERNAME,
        ):
            with contextlib.suppress(PasswordDeleteError):
                keyring.delete_password(KEYRING_SERVICE_NAME, key)

        logger.info("Removed keyring entries")
    except Exception as e:
        logger.warning(f"Failed to remove keyring entries: {e}")


def _remove_start_menu_shortcut() -> None:
    """Remove the Start Menu shortcut if it exists."""
    try:
        shortcut_path = get_default_program_shortcut_destination()
        if shortcut_path.exists():
            shortcut_path.unlink()
            logger.info(f"Removed shortcut: {shortcut_path}")
    except Exception as e:
        logger.warning(f"Failed to remove shortcut: {e}")


def _remove_config_and_cache() -> None:
    """Remove config files and cache directory."""
    # Remove user config directory
    try:
        config_dir = Path(get_config_path())
        if config_dir.is_dir():
            shutil.rmtree(config_dir, ignore_errors=True)
            logger.info(f"Removed config directory: {config_dir}")
    except Exception as e:
        logger.warning(f"Failed to remove config directory: {e}")

    # Remove cache directory if different from config
    try:
        cache_dir = get_cache_path()
        if cache_dir.is_dir() and cache_dir != Path(get_config_path()):
            shutil.rmtree(cache_dir, ignore_errors=True)
            logger.info(f"Removed cache directory: {cache_dir}")
    except Exception as e:
        logger.warning(f"Failed to remove cache directory: {e}")

    # Remove local portable config if it exists
    try:
        local_cfg = local_config()
        if local_cfg.is_file():
            local_cfg.unlink()
            logger.info(f"Removed local config: {local_cfg}")
    except Exception as e:
        logger.warning(f"Failed to remove local config: {e}")


def _remove_winget_package_dir() -> None:
    """Remove the winget package directory if the app was installed via winget.

    When winget installs a portable package, it places the exe under
    %LOCALAPPDATA%\\Microsoft\\WinGet\\Packages\\<PackageId>__<Source>\\.
    """
    try:
        winget_packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        if not winget_packages.is_dir():
            return

        package_id = "VictorIX.BlenderLauncher"
        for entry in winget_packages.iterdir():
            if entry.is_dir() and entry.name.startswith(package_id):
                shutil.rmtree(entry, ignore_errors=True)
                logger.info(f"Removed winget package directory: {entry}")
    except Exception as e:
        logger.warning(f"Failed to remove winget package directory: {e}")


def _schedule_self_deletion() -> None:
    """Schedule deletion of the executable after the process exits.

    Uses a detached cmd process that waits briefly then deletes the exe
    and its parent directory if empty.
    """
    try:
        exe_path = Path(sys.executable).resolve()
        exe_dir = exe_path.parent

        cmd = f'cmd.exe /c "ping -n 3 127.0.0.1 > nul && del /f /q "{exe_path}" && rmdir "{exe_dir}""'

        subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        logger.info("Scheduled self-deletion")
    except Exception as e:
        logger.warning(f"Failed to schedule self-deletion: {e}")
