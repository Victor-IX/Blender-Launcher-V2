import contextlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def register_with_winget(exe_path: str | Path, version: str) -> bool:
    """
    Register the application with WinGet by creating ARP registry entries.

    WinGet uses the Windows Add/Remove Programs (ARP) registry to track installed applications.
    By creating the correct registry entries, the normal installation will be recognized as
    a WinGet-managed package, allowing `winget update` to work.

    Args:
        exe_path: Path to the executable
        version: Application version (e.g., "2.5.3")

    Returns:
        True if registration was successful, False otherwise
    """
    if sys.platform != "win32":
        logger.debug("WinGet registration is only supported on Windows")
        return False

    try:
        import winreg

        exe_path = Path(exe_path).resolve()
        install_location = exe_path.parent
        package_id = "VictorIX.BlenderLauncher"

        if _has_winget_tracking_key(winreg, package_id):
            logger.debug(f"Winget tracking key already exists for {package_id}, skipping registration")
            return True

        # Registry path for uninstall information
        # Using HKEY_CURRENT_USER to avoid requiring admin privileges
        registry_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{package_id}"

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            # Required fields for WinGet recognition
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Blender Launcher")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "VictorIX")

            # Installation location
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_location))

            # Executable path
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))

            # Uninstall command for winget
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall')
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{exe_path}" uninstall --quiet')

            # Remove legacy NoRemove flag from older versions
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, "NoRemove")

            # WinGet-specific markers
            # This helps WinGet identify the package
            winreg.SetValueEx(key, "WinGetPackageIdentifier", 0, winreg.REG_SZ, package_id)
            winreg.SetValueEx(key, "WinGetSourceIdentifier", 0, winreg.REG_SZ, "winget")

            logger.info(f"Successfully registered with WinGet: {package_id} v{version}")

        return True

    except Exception as e:
        logger.error(f"Failed to register with WinGet: {e}")
        return False


def unregister_from_winget() -> bool:
    if sys.platform != "win32":
        logger.debug("WinGet unregistration is only supported on Windows")
        return False

    try:
        import winreg

        package_id = "VictorIX.BlenderLauncher"
        uninstall_root = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"

        # Delete our own ARP key
        with contextlib.suppress(FileNotFoundError):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"{uninstall_root}\{package_id}")
            logger.info(f"Successfully unregistered from WinGet: {package_id}")

        _remove_winget_tracking_keys(winreg, package_id)

    except Exception as e:
        logger.error(f"Failed to unregister from WinGet: {e}")
        return False
    return True


def _has_winget_tracking_key(winreg, package_id: str) -> bool:
    """Check if there is winget tracking key for this package."""
    uninstall_root = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_root) as root_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(root_key, i)
                    if subkey_name.startswith(package_id):
                        return True
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    return False


def _remove_winget_tracking_keys(winreg, package_id: str) -> None:
    """Remove winget tracking keys (e.g. VictorIX.BlenderLauncher__DefaultSource)."""
    uninstall_root = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_root) as root_key:
            i = 0
            keys_to_delete = []
            while True:
                try:
                    subkey_name = winreg.EnumKey(root_key, i)
                    if subkey_name.startswith(package_id):
                        keys_to_delete.append(subkey_name)
                    i += 1
                except OSError:
                    break

            for subkey_name in keys_to_delete:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"{uninstall_root}\{subkey_name}")
                    logger.info(f"Removed winget tracking key: {subkey_name}")
    except FileNotFoundError:
        pass


def is_registered_with_winget() -> bool:
    if sys.platform != "win32":
        return False

    try:
        import winreg

        package_id = "VictorIX.BlenderLauncher"
        return _has_winget_tracking_key(winreg, package_id)

    except Exception as e:
        logger.error(f"Error checking WinGet registration: {e}")
        return False
