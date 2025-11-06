import contextlib
import logging
import os
import sys
from pathlib import Path
from shutil import copyfile

from modules._platform import get_cache_path, get_cwd, get_platform, is_frozen
from modules.icons import get_bl_file_location
from modules.settings import get_library_folder


# TODO: Remove this duplicate code generate_program_shortcut()
def generate_blender_shortcut(folder, name, destination: Path):
    platform = get_platform()
    library_folder = Path(get_library_folder())

    if sys.platform == "win32":
        import win32com.client
        from win32comext.shell import shell, shellcon

        targetpath = library_folder / folder / "blender.exe"
        workingdir = library_folder / folder

        if getattr(sys, "frozen", False):
            icon = sys._MEIPASS + "/files/winblender.ico"  # noqa: SLF001
        else:
            icon = Path("./source/resources/icons/winblender.ico").resolve().as_posix()

        icon_location = library_folder / folder / "winblender.ico"
        copyfile(icon, icon_location.as_posix())

        _WSHELL = win32com.client.Dispatch("Wscript.Shell")
        wscript = _WSHELL.CreateShortCut(destination.as_posix())
        wscript.Targetpath = targetpath.as_posix()
        wscript.WorkingDirectory = workingdir.as_posix()
        wscript.WindowStyle = 0
        wscript.IconLocation = icon_location.as_posix()
        wscript.save()
    elif platform == "Linux":
        _exec = library_folder / folder / "blender"
        icon = library_folder / folder / "blender.svg"

        kws = (
            "3d;cg;modeling;animation;painting;"
            "sculpting;texturing;video editing;"
            "video tracking;rendering;render engine;"
            "cycles;game engine;python;"
        )

        desktop_entry = "\n".join(
            [
                "[Desktop Entry]",
                f"Name={name}",
                "Comment=3D modeling, animation, rendering and post-production",
                f"Keywords={kws}",
                "Icon={}".format(icon.as_posix().replace(" ", r"\ ")),
                "Terminal=false",
                "Type=Application",
                "Categories=Graphics;3DGraphics;",
                "MimeType=application/x-blender;",
                "Exec={} %f".format(_exec.as_posix().replace(" ", r"\ ")),
            ]
        )
        with open(destination, "w", encoding="utf-8") as file:
            file.write(desktop_entry)

        os.chmod(destination, 0o744)


def association_is_registered() -> bool:
    assert sys.platform == "win32"
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\blenderlauncherv2.blend",
        ):
            return True
    except FileNotFoundError:
        ...
    return False


def register_windows_filetypes(exe=sys.executable):
    assert sys.platform == "win32"

    import winreg

    # Register the program in the classes
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\blenderlauncherv2.blend\shell\open\command",
    ) as command_key:
        if is_frozen():
            pth = f'"{Path(exe).resolve()}"'
        else:
            pth = f'"{Path(sys.argv[0]).resolve()}"'

        winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, f'{pth} "%1"')
        logging.debug("Registered blenderlauncherv2.blend")

    # add it to the OpenWithProgids list for .blend
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\.blend\OpenWithProgids",
    ) as progids_key:
        winreg.SetValueEx(progids_key, "blenderlauncherv2.blend", 0, winreg.REG_SZ, "")
        logging.debug(r"Added blenderlauncherv2.blend to .blend\OpenWithProgids")

    # Extract and save the bl_file.ico
    file_icon_path = get_bl_file_location()
    desired_location = get_cache_path() / "bl_file.ico"

    if not desired_location.exists():
        copyfile(file_icon_path, desired_location)
        logging.debug(f"Extracted and saved bl_file.ico to {desired_location}")

    # add it to the DefaultIcon key for blenderlauncherv2.blend
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\blenderlauncherv2.blend\DefaultIcon",
    ) as di_key:
        winreg.SetValueEx(di_key, "", 0, winreg.REG_SZ, str(desired_location))
        logging.debug(r"Added bl_file.ico to DefaultIcon")

    logging.info("Finished registering Blender Launcher for file associations")


def unregister_windows_filetypes():
    assert sys.platform == "win32"

    import winreg

    # Unregister the program in the classes
    for key in (
        r"Software\Classes\blenderlauncherv2.blend\shell\open\command",
        r"Software\Classes\blenderlauncherv2.blend\shell\open",
        r"Software\Classes\blenderlauncherv2.blend\shell",
        r"Software\Classes\blenderlauncherv2.blend\DefaultIcon",
        r"Software\Classes\blenderlauncherv2.blend",
    ):
        with contextlib.suppress(FileNotFoundError):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
            logging.debug(f"Deleted key {key}")

    # remove it from the OpenWithProgids list
    with (
        winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\.blend\OpenWithProgids",
            access=winreg.KEY_SET_VALUE,
        ) as command_key,
        contextlib.suppress(FileNotFoundError),
    ):
        winreg.DeleteValue(command_key, "blenderlauncherv2.blend")
        logging.debug("Deleted value blenderlauncherv2.blend from .blend\\OpenWithProgids")

    # remove it from the OpenWithProgids list for .blend1
    # we need to keep this for deprecation purposes
    with (
        winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\.blend1\OpenWithProgids",
            access=winreg.KEY_SET_VALUE,
        ) as command_key,
        contextlib.suppress(FileNotFoundError),
    ):
        winreg.DeleteValue(command_key, "blenderlauncherv2.blend")
        logging.debug("Deleted value blenderlauncherv2.blend from .blend1\\OpenWithProgids")

    logging.info("Finished Unregistering blenderlauncher for file associations")


def get_shortcut_type() -> str:
    """ONLY FOR VISUAL REPRESENTATION"""
    return {
        "Windows": "Shortcut",
        "Linux": "Desktop file",
    }.get(get_platform(), "Shortcut")


def get_default_program_shortcut_destination():
    """Returns the default folder to where a shortcut to Blender Launcher should be saved."""
    return get_default_shortcut_destination("Blender Launcher")


def get_default_shortcut_destination(shortcut_name):
    """Returns the default folder to where a shortcut with name 'shortcut_name' should be saved."""
    # TODO: Default to desktop if shortcut already exist in start menu
    platform = get_platform()
    folder = get_default_shortcut_folder()

    if platform == "Windows":
        return Path(folder / (shortcut_name + ".lnk"))

    return Path(folder / (shortcut_name.replace(" ", "-") + ".desktop"))


def get_default_shortcut_folder():
    """Returns the default folder to where shortcuts should be saved."""
    platform = get_platform()

    if platform == "Windows":
        return Path(Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    elif platform == "Linux":
        return Path(Path.home() / ".local" / "share" / "applications")

    return Path.home()


def generate_program_shortcut(destination: Path, exe=sys.executable):
    """Generates a shortcut for this program. Also sets up filetype associations in Linux."""
    platform = get_platform()

    if sys.platform == "win32":
        import win32com.client
        import pythoncom

        dest = destination.with_suffix(".lnk").as_posix()
        # create the shortcut
        _WSHELL = win32com.client.Dispatch("Wscript.Shell", pythoncom.CoInitialize())
        wscript = _WSHELL.CreateShortcut(str(dest))

        wscript.Targetpath = exe
        args = ""
        if not is_frozen():
            main_py = Path(sys.argv[0]).resolve()

            args = str(main_py)

            # Icon location would be source/resources/icons/bl/bl.ico
            icon_loc = Path(main_py.parent, "resources", "icons", "bl", "bl.ico")

            wscript.IconLocation = icon_loc.as_posix()

        wscript.Arguments = args

        wscript.WorkingDirectory = get_cwd().as_posix()
        wscript.WindowStyle = 0
        wscript.save()

    elif platform == "Linux":
        import shlex

        if is_frozen():
            source = shlex.quote(exe)
        else:
            exe = Path(exe)
            source = f"{shlex.quote(str(exe))} {shlex.quote(str(Path(sys.argv[0]).resolve()))}"

        text = "\n".join(
            [
                "[Desktop Entry]",
                "Name=Blender Launcher",
                "GenericName=Launcher",
                f"Exec={source}",
                "MimeType=application/x-blender;",
                "Icon=blender-icon",
                "Terminal=false",
                "Type=Application",
                "Categories=Graphics;3DGraphics",
            ]
        )

        with destination.open("w", encoding="utf-8") as file:
            file.write(text)

        os.chmod(destination, 0o744)
