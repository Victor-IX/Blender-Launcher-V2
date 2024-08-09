import contextlib
import logging
import os
import sys
from pathlib import Path
from shutil import copyfile

from modules._platform import get_cwd, get_launcher_name, get_platform, is_frozen
from modules.settings import get_library_folder


def create_shortcut(folder, name):
    platform = get_platform()
    library_folder = Path(get_library_folder())

    if sys.platform == "win32":
        import win32com.client
        from win32comext.shell import shell, shellcon

        targetpath = library_folder / folder / "blender.exe"
        workingdir = library_folder / folder
        desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, None, 0)
        dist = Path(desktop) / (name + ".lnk")

        if getattr(sys, "frozen", False):
            icon = sys._MEIPASS + "/files/winblender.ico"  # noqa: SLF001
        else:
            icon = Path("./resources/icons/winblender.ico").resolve().as_posix()

        icon_location = library_folder / folder / "winblender.ico"
        copyfile(icon, icon_location.as_posix())

        _WSHELL = win32com.client.Dispatch("Wscript.Shell")
        wscript = _WSHELL.CreateShortCut(dist.as_posix())
        wscript.Targetpath = targetpath.as_posix()
        wscript.WorkingDirectory = workingdir.as_posix()
        wscript.WindowStyle = 0
        wscript.IconLocation = icon_location.as_posix()
        wscript.save()
    elif platform == "Linux":
        _exec = library_folder / folder / "blender"
        icon = library_folder / folder / "blender.svg"
        desktop = Path.home() / "Desktop"
        filename = name.replace(" ", "-")
        dist = desktop / (filename + ".desktop")

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
        with open(dist, "w", encoding="utf-8") as file:
            file.write(desktop_entry)

        os.chmod(dist, 0o744)


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


def register_windows_filetypes():
    assert sys.platform == "win32"

    import winreg

    # Register the program in the classes
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\blenderlauncherv2.blend\shell\open\command",
    ) as command_key:
        if is_frozen():
            pth = f'"{Path(sys.executable).resolve()}"'
        else:
            pth = f'"{Path(sys.executable).resolve()}" "{Path(sys.argv[0]).resolve()}"'

        winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, f'{pth} __launch_target "%1"')

    # add it to the OpenWithProgids list
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\.blend\OpenWithProgids",
    ) as progids_key:
        winreg.SetValueEx(progids_key, "blenderlauncherv2.blend", 0, winreg.REG_SZ, "")

    # addit to the OpenWithProgids list for .blend1
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\.blend1\OpenWithProgids",
    ) as progids_key:
        winreg.SetValueEx(progids_key, "blenderlauncherv2.blend", 0, winreg.REG_SZ, "")

    logging.info("Registered blenderlauncher for file associations")


def unregister_windows_filetypes():
    assert sys.platform == "win32"

    import winreg

    # Unregister the program in the classes
    with contextlib.suppress(FileNotFoundError):
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\blenderlauncherv2.blend\shell\open\command")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\blenderlauncherv2.blend\shell\open")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\blenderlauncherv2.blend\shell")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\blenderlauncherv2.blend")

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

    # remove it from the OpenWithProgids list for .blend1
    with (
        winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\.blend1\OpenWithProgids",
            access=winreg.KEY_SET_VALUE,
        ) as command_key,
        contextlib.suppress(FileNotFoundError),
    ):
        winreg.DeleteValue(command_key, "blenderlauncherv2.blend")

    logging.info("Unregistered blenderlauncher for file associations")


def get_shortcut_type() -> str:
    """ONLY FOR VISUAL REPRESENTATION"""
    return {
        "Windows": "Shortcut",
        "Linux": "Desktop file",
    }.get(get_platform(), "Shortcut")


def get_default_shortcut_destination():
    return {
        "Windows": Path(
            Path.home(), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Blender Launcher V2"
        ),
        "Linux": Path(Path.home(), ".local", "share", "applications", "BLV2.desktop"),
    }.get(get_platform(), Path(Path.home(), ".local", "share", "applications", "BLV2.desktop"))


def generate_program_shortcut(destination: Path):
    """Generates a shortcut for this program. Also sets up filetype associations in Linux."""
    platform = get_platform()

    if sys.platform == "win32":
        import win32com.client

        dest = destination.with_suffix(".lnk").as_posix()
        # create the shortcut
        _WSHELL = win32com.client.Dispatch("Wscript.Shell")
        wscript = _WSHELL.CreateShortcut(str(dest))

        exe = sys.executable

        wscript.Targetpath = exe
        args = "__launch_target"
        if not is_frozen():
            main_py = Path(sys.argv[0]).resolve()

            args = f"{main_py} {args}"

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
            bl_exe, _ = get_launcher_name()
            cwd = get_cwd()
            source = shlex.quote(str(cwd / bl_exe))
        else:
            exe = Path(sys.executable)
            source = f"{shlex.quote(str(exe))} {shlex.quote(str(Path(sys.argv[0]).resolve()))}"

        _exec = source
        text = "\n".join(
            [
                "[Desktop Entry]",
                "Name=Blender Launcher V2",
                "GenericName=Launcher",
                f"Exec={_exec} __launch_target",
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
