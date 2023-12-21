import contextlib
import sys
from pathlib import Path

from modules._platform import get_cwd, get_platform
from PyQt5.QtCore import QSettings

if get_platform() == "Windows":
    import winreg

tabs = {
    "Library": 0,
    "Downloads": 1,
    "User": 2
}

library_pages = {
    "Stable Releases": 0,
    "Daily Builds": 1,
    "Experimental Branches": 2
}


downloads_pages = {
    "Stable Releases": 0,
    "Daily Builds": 1,
    "Experimental Branches": 2
}


favorite_pages = {
    "Disable": 0,
    "Stable Releases": 1,
    "Daily Builds": 2,
    "Experimental Branches": 3
}


library_subfolders = [
    "custom",
    "stable",
    "daily",
    "experimental",
    "template"
]


proxy_types = {
    "None": 0,
    "HTTP": 1,
    "HTTPS": 2,
    "SOCKS4": 3,
    "SOCKS5": 4
}


def get_settings():
    return QSettings((get_cwd() / "Blender Launcher.ini").as_posix(),
                     QSettings.IniFormat)


def get_library_folder():
    settings = get_settings()
    library_folder = settings.value("library_folder")

    if not is_library_folder_valid(library_folder):
        library_folder = get_cwd()
        settings.setValue("library_folder", library_folder)

    return library_folder


def is_library_folder_valid(library_folder=None):
    if library_folder is None:
        library_folder = get_settings().value("library_folder")

    if (library_folder is not None) and Path(library_folder).exists():
        try:
            (Path(library_folder) / ".temp").mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return False

        return True

    return False


def set_library_folder(new_library_folder):
    settings = get_settings()

    if is_library_folder_valid(new_library_folder) is True:
        settings.setValue("library_folder", new_library_folder)
        create_library_folders(new_library_folder)
        return True

    return False


def create_library_folders(library_folder):
    for subfolder in library_subfolders:
        (Path(library_folder) / subfolder).mkdir(parents=True, exist_ok=True)


def get_favorite_path():
    return get_settings().value("Internal/favorite_path")


def set_favorite_path(path):
    get_settings().setValue("Internal/favorite_path", path)


def get_launch_when_system_starts():
    if get_platform() == "Windows":
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
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
    if get_platform() == "Windows":
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)

        if (is_checked):
            path = sys.executable
            winreg.SetValueEx(key, "Blender Launcher",
                              0, winreg.REG_SZ, path)
        else:
            with contextlib.suppress(Exception):
                winreg.DeleteValue(key, "Blender Launcher")

        key.Close()


def get_launch_minimized_to_tray():
    return get_settings().value("launch_minimized_to_tray", type=bool)


def set_launch_minimized_to_tray(is_checked):
    get_settings().setValue("launch_minimized_to_tray", is_checked)


def get_enable_high_dpi_scaling():
    return get_settings().value("enable_high_dpi_scaling", defaultValue=True, type=bool)

def set_enable_high_dpi_scaling(is_checked):
    get_settings().setValue("enable_high_dpi_scaling", is_checked)


def get_sync_library_and_downloads_pages():
    return get_settings().value("sync_library_and_downloads_pages", defaultValue=True, type=bool)

def set_sync_library_and_downloads_pages(is_checked):
    get_settings().setValue("sync_library_and_downloads_pages", is_checked)


def get_default_library_page():
    return get_settings().value("default_library_page", defaultValue=0, type=int)


def set_default_library_page(page):
    get_settings().setValue("default_library_page", library_pages[page])


def get_mark_as_favorite():
    return get_settings().value("mark_as_favorite", defaultValue=0, type=int)

def set_mark_as_favorite(page):
    get_settings().setValue("mark_as_favorite", favorite_pages[page])


def get_default_downloads_page():
    return get_settings().value("default_downloads_page", defaultValue=0, type=int)


def set_default_downloads_page(page):
    get_settings().setValue("default_downloads_page", downloads_pages[page])


def get_default_tab():
    return get_settings().value("default_tab", defaultValue=0, type=int)

def set_default_tab(tab):
    get_settings().setValue("default_tab", tabs[tab])


def get_list_sorting_type(list_name):
    return get_settings().value(f"Internal/{list_name}_sorting_type", defaultValue=1, type=int)

def set_list_sorting_type(list_name, sorting_type):
    get_settings().setValue(f"Internal/{list_name}_sorting_type", sorting_type.value)


def get_enable_new_builds_notifications():
    return get_settings().value("enable_new_builds_notifications", defaultValue=True, type=bool)

def set_enable_new_builds_notifications(is_checked):
    get_settings().setValue("enable_new_builds_notifications", is_checked)


def get_enable_download_notifications():
    return get_settings().value("enable_download_notifications", defaultValue=True, type=bool)

def set_enable_download_notifications(is_checked):
    get_settings().setValue("enable_download_notifications", is_checked)


def get_blender_startup_arguments():
    args = get_settings().value("blender_startup_arguments")

    if args is None:
        return ""
    return args.strip()


def set_blender_startup_arguments(args):
    get_settings().setValue("blender_startup_arguments", args.strip())


def get_bash_arguments():
    return get_settings().value("bash_arguments", defaultValue="", type=str).strip()



def set_bash_arguments(args):
    get_settings().setValue("bash_arguments", args.strip())


def get_install_template():
    return get_settings().value("install_template", type=bool)


def set_install_template(is_checked):
    get_settings().setValue("install_template", is_checked)


def get_show_tray_icon():
    return get_settings().value("show_tray_icon", defaultValue=True, type=bool)

def set_show_tray_icon(is_checked):
    get_settings().setValue("show_tray_icon", is_checked)


def get_launch_blender_no_console():
    return get_settings().value("launch_blender_no_console", type=bool)


def set_launch_blender_no_console(is_checked):
    get_settings().setValue("launch_blender_no_console", is_checked)


def get_quick_launch_key_seq():
    return get_settings().value("quick_launch_key_seq", defaultValue="alt+f11", type=str).strip()


def set_quick_launch_key_seq(key_seq):
    get_settings().setValue("quick_launch_key_seq", key_seq.strip())


def get_enable_quick_launch_key_seq():
    return get_settings().value("enable_quick_launch_key_seq", defaultValue=False, type=bool)


def set_enable_quick_launch_key_seq(is_checked):
    get_settings().setValue("enable_quick_launch_key_seq", is_checked)


def get_proxy_type():
    return get_settings().value("proxy/type", defaultValue=0, type=int)

def set_proxy_type(proxy_type):
    get_settings().setValue("proxy/type", proxy_types[proxy_type])


def get_proxy_host():
    host = get_settings().value("proxy/host")

    if host is None:
        return "255.255.255.255"
    return host.strip()


def set_proxy_host(args):
    get_settings().setValue("proxy/host", args.strip())


def get_proxy_port():
    port = get_settings().value("proxy/port")

    if port is None:
        return "99999"
    return port.strip()


def set_proxy_port(args):
    get_settings().setValue("proxy/port", args.strip())


def get_proxy_user():
    user = get_settings().value("proxy/user")

    if user is None:
        return ""
    return user.strip()


def set_proxy_user(args):
    get_settings().setValue("proxy/user", args.strip())


def get_proxy_password():
    password = get_settings().value("proxy/password")

    if password is None:
        return ""
    return password.strip()


def set_proxy_password(args):
    get_settings().setValue("proxy/password", args.strip())


def get_use_custom_tls_certificates():
    return get_settings().value("use_custom_tls_certificates", defaultValue=True, type=bool)

def set_use_custom_tls_certificates(is_checked):
    get_settings().setValue("use_custom_tls_certificates", is_checked)


def get_check_for_new_builds_automatically():
    settings = get_settings()

    if settings.contains("check_for_new_builds_automatically"):
        return settings.value("check_for_new_builds_automatically", type=bool)
    return False


def set_check_for_new_builds_automatically(is_checked):
    get_settings().setValue("check_for_new_builds_automatically", is_checked)


def get_new_builds_check_frequency():
    """Time in seconds"""

    settings = get_settings()

    if settings.contains("new_builds_check_frequency"):
        return settings.value("new_builds_check_frequency", type=int)
    return 600


def set_new_builds_check_frequency(frequency):
    get_settings().setValue("new_builds_check_frequency", frequency)


def get_minimum_blender_stable_version() -> float:
    return get_settings().value("minimum_blender_stable_version", defaultValue=3.0, type=float)

def set_minimum_blender_stable_version(v: float):
    get_settings().setValue("minimum_blender_stable_version", v)
