import contextlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_PACKAGE_ID = "VictorIX.BlenderLauncher"
_UNINSTALL_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"


def register_with_winget(exe_path: str | Path, version: str) -> bool:
    """Register the application in the Windows ARP (Add/Remove Programs) registry.

    Args:
        exe_path: Path to the executable.
        version: Application version string (e.g. "2.5.3").

    Returns:
        True if registration was successful, False otherwise.
    """
    if sys.platform != "win32":
        logger.debug("WinGet registration is only supported on Windows")
        return False

    try:
        import winreg

        exe_path = Path(exe_path).resolve()
        install_location = exe_path.parent

        if _has_winget_tracking_key(winreg, _PACKAGE_ID):
            _update_winget_tracking_key(winreg, _PACKAGE_ID, exe_path, version)
            _delete_arp_key(winreg, _PACKAGE_ID)
            return True

        registry_path = rf"{_UNINSTALL_ROOT}\{_PACKAGE_ID}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Blender Launcher")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "VictorIX")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_location))
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall')
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall --quiet')
            winreg.SetValueEx(key, "WinGetPackageIdentifier", 0, winreg.REG_SZ, _PACKAGE_ID)
            winreg.SetValueEx(key, "WinGetSourceIdentifier", 0, winreg.REG_SZ, "winget")
            # Remove legacy NoRemove flag from older versions
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, "NoRemove")

            logger.info(f"Registered app ARP key: {_PACKAGE_ID} v{version}")

        return True

    except Exception as e:
        logger.error(f"Failed to register with WinGet: {e}")
        return False


def unregister_from_winget(exe_path: str | Path | None = None, version: str | None = None) -> bool:
    """Remove winget management and switch to a self-managed ARP entry.

    Args:
        exe_path: Path to the current executable (used to write the self-managed ARP key).
        version: Current application version string.

    Returns:
        True if unregistration was successful, False otherwise.
    """
    if sys.platform != "win32":
        logger.debug("WinGet unregistration is only supported on Windows")
        return False

    try:
        import winreg

        # Remove winget tracking keys first
        _remove_winget_tracking_keys(winreg, _PACKAGE_ID)

        if exe_path is not None and version is not None:
            # Re-create the app-owned key so the app stays in Windows Settings
            exe_path = Path(exe_path).resolve()
            install_location = exe_path.parent
            registry_path = rf"{_UNINSTALL_ROOT}\{_PACKAGE_ID}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Blender Launcher")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "VictorIX")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_location))
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall')
                winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall --quiet')
                winreg.SetValueEx(key, "WinGetPackageIdentifier", 0, winreg.REG_SZ, _PACKAGE_ID)
                winreg.SetValueEx(key, "WinGetSourceIdentifier", 0, winreg.REG_SZ, "winget")
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, "NoRemove")
            logger.info(f"Switched to self-managed ARP key: {_PACKAGE_ID} v{version}")
        else:
            _delete_arp_key(winreg, _PACKAGE_ID)
            logger.info(f"Removed ARP key: {_PACKAGE_ID}")

    except Exception as e:
        logger.error(f"Failed to unregister from WinGet: {e}")
        return False
    return True


def _has_arp_key(winreg, package_id: str) -> bool:
    """Check if the app's own ARP key exists (exact match, not winget tracking keys)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{_UNINSTALL_ROOT}\{package_id}"):
            return True
    except FileNotFoundError:
        return False


def _delete_arp_key(winreg, package_id: str) -> None:
    """Delete the app-owned ARP key if it exists."""
    with contextlib.suppress(FileNotFoundError):
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"{_UNINSTALL_ROOT}\{package_id}")
        logger.info(f"Removed app ARP key: {package_id}")


def _has_winget_tracking_key(winreg, package_id: str) -> bool:
    """Check if a genuine winget tracking key exists (e.g. VictorIX.BlenderLauncher_Microsoft.Winget.Source_...)."""
    tracking_prefix = package_id + "_"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _UNINSTALL_ROOT) as root_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(root_key, i)
                    if subkey_name.startswith(tracking_prefix):
                        return True
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    return False


def _update_winget_tracking_key(winreg, package_id: str, exe_path: Path, version: str) -> None:
    """Update version and exe paths in all existing winget tracking keys."""
    tracking_prefix = package_id + "_"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _UNINSTALL_ROOT) as root_key:
            i = 0
            tracking_keys = []
            while True:
                try:
                    subkey_name = winreg.EnumKey(root_key, i)
                    if subkey_name.startswith(tracking_prefix):
                        tracking_keys.append(subkey_name)
                    i += 1
                except OSError:
                    break

        for subkey_name in tracking_keys:
            with contextlib.suppress(Exception):
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    rf"{_UNINSTALL_ROOT}\{subkey_name}",
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
                    winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(exe_path.parent))
                    winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))
                    winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall')
                    winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall --quiet')
                logger.info(f"Updated winget tracking key: {subkey_name} → v{version}")
    except FileNotFoundError:
        pass


def _remove_winget_tracking_keys(winreg, package_id: str) -> None:
    """Remove winget tracking keys (e.g. VictorIX.BlenderLauncher_Microsoft.Winget.Source_...)."""
    tracking_prefix = package_id + "_"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _UNINSTALL_ROOT) as root_key:
            i = 0
            keys_to_delete = []
            while True:
                try:
                    subkey_name = winreg.EnumKey(root_key, i)
                    if subkey_name.startswith(tracking_prefix):
                        keys_to_delete.append(subkey_name)
                    i += 1
                except OSError:
                    break

        for subkey_name in keys_to_delete:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"{_UNINSTALL_ROOT}\{subkey_name}")
                logger.info(f"Removed winget tracking key: {subkey_name}")
    except FileNotFoundError:
        pass


def is_registered_with_winget() -> bool:
    """Return True if the app has any ARP entry (own key or a winget tracking key)."""
    if sys.platform != "win32":
        return False

    try:
        import winreg

        return _has_arp_key(winreg, _PACKAGE_ID) or _has_winget_tracking_key(winreg, _PACKAGE_ID)

    except Exception as e:
        logger.error(f"Error checking WinGet registration: {e}")
        return False
