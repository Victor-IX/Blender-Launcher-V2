import argparse
import os
import platform
import sys
from functools import cache
from pathlib import Path
from subprocess import DEVNULL, PIPE, STDOUT, Popen, call, check_call, check_output
from tempfile import NamedTemporaryFile


@cache
def get_platform():
    platforms = {
        "linux": "Linux",
        "linux1": "Linux",
        "linux2": "Linux",
        "darwin": "macOS",
        "win32": "Windows",
    }

    if sys.platform not in platforms:
        return sys.platform

    return platforms[sys.platform]


@cache
def get_architecture():
    return platform.machine().lower()


@cache
def get_launcher_name():
    if sys.platform == "win32":
        return ("Blender Launcher.exe", "Blender Launcher Updater.exe")

    return ("Blender Launcher", "Blender Launcher Updater")


@cache
def get_platform_full():
    return f"{get_platform()}-{platform.release()}"


def show_windows_help(parser: argparse.ArgumentParser):
    with (
        NamedTemporaryFile("w+", suffix=".bat", delete=False) as f,
        NamedTemporaryFile("w+", suffix=".txt", delete=False) as help_txt_file,
    ):
        help_txt_file.write(parser.format_help())
        help_txt_file.flush()
        help_txt_file.close()

        lines = [f"echo{' ' + line if line else '.'}" for line in parser.format_help().splitlines()]
        echos = "\n".join(lines)
        f.write(
            f"""
            @echo off
            cls
            {echos}
            pause
            """
        )

        f.flush()
        f.close()
        call(["cmd", "/c", f.name])
        try:
            os.unlink(f.name)
            os.unlink(help_txt_file.name)
        except FileNotFoundError:
            pass


def get_environment():
    # Make a copy of the environment
    env = dict(os.environ)
    # For GNU/Linux and *BSD
    lp_key = "LD_LIBRARY_PATH"
    lp_orig = env.get(lp_key + "_ORIG")

    if lp_orig is not None:
        # Restore the original, unmodified value
        env[lp_key] = lp_orig
    else:
        # This happens when LD_LIBRARY_PATH was not set
        # Remove the env var as a last resort
        env.pop(lp_key, None)

    # Removing PyInstaller variables from the environment
    env.pop("_MEIPASS", None)

    for key in list(env.keys()):
        if key.startswith("_PYI"):
            env.pop(key)

    if "PATH" in env:
        paths = env["PATH"].split(os.pathsep)
        paths = [p for p in paths if "_MEI" not in p and "pyi" not in p.lower()]
        env["PATH"] = os.pathsep.join(paths)
    return env


def _popen(args):
    env = get_environment()
    if get_platform() == "Windows":
        DETACHED_PROCESS = 0x00000008
        return Popen(
            args,
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
            creationflags=DETACHED_PROCESS,
            start_new_session=True,
            env=env,
        )

    return Popen(
        args,
        shell=True,
        stdout=None,
        stderr=None,
        close_fds=True,
        preexec_fn=os.setpgrp,  # type: ignore
        env=env,
    )


def _check_call(args):
    platform = get_platform()

    if platform == "Windows":
        from subprocess import CREATE_NO_WINDOW

        return check_call(args, creationflags=CREATE_NO_WINDOW, shell=True, stderr=DEVNULL, stdin=DEVNULL)

    return check_call(args, shell=False, stderr=DEVNULL, stdin=DEVNULL)


def _call(args):
    platform = get_platform()

    if platform == "Windows":
        from subprocess import CREATE_NO_WINDOW

        call(args, creationflags=CREATE_NO_WINDOW, shell=True, stdout=PIPE, stderr=STDOUT, stdin=DEVNULL)
    elif platform == "Linux":
        pass


def _check_output(args):
    platform = get_platform()

    if platform == "Windows":
        from subprocess import CREATE_NO_WINDOW

        return check_output(args, creationflags=CREATE_NO_WINDOW, shell=True, stderr=DEVNULL, stdin=DEVNULL)

    return check_output(args, shell=False, stderr=DEVNULL, stdin=DEVNULL)


@cache
def is_frozen():
    """
    This function checks if the application is running as a bundled executable
    using a package like PyInstaller. It returns True if the application is "frozen"
    (i.e., bundled as an executable) and False otherwise.
    """

    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


@cache
def get_cwd():
    if is_frozen():
        return Path(os.path.dirname(sys.executable))

    return Path.cwd()


@cache
def get_config_path():
    platform = get_platform()

    config_path = ""
    if platform == "Windows":
        config_path = os.getenv("LOCALAPPDATA")
    elif platform == "Linux":
        # Borrowed from platformdirs
        path = os.environ.get("XDG_CONFIG_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.config")
        config_path = path
    elif platform == "macOS":
        config_path = os.path.expanduser("~/Library/Application Support")

    if not config_path:
        return get_cwd()
    return os.path.join(config_path, "Blender Launcher")


@cache
def local_config():
    return get_cwd() / "Blender Launcher.ini"


@cache
def user_config():
    return Path(get_config_path()) / "Blender Launcher.ini"


def get_config_file():
    # Prioritize local settings for portability
    if (local := local_config()).exists():
        return local
    return user_config()


@cache
def get_cache_path():
    platform = get_platform()

    cache_path = ""
    if platform == "Windows":
        cache_path = os.getenv("LOCALAPPDATA")
    elif platform == "Linux":
        # Borrowed from platformdirs
        cache_path = os.environ.get("XDG_CACHE_HOME", "")
        if not cache_path.strip():
            cache_path = os.path.expanduser("~/.cache")
    elif platform == "macOS":
        cache_path = os.path.expanduser("~/Library/Logs")
    if not cache_path:
        return os.getcwd()
    return os.path.join(cache_path, "Blender Launcher")


def stable_cache_path():
    return Path(get_cache_path(), "stable_builds.json")


def bfa_cache_path():
    return Path(get_cache_path(), "bforartists_builds.json")


def get_blender_config_folder(custom_folder: str = None):
    """
    Retrieves the Blender configuration folder.
    :param custom_folder: Optional; a custom folder name use to locate fork blender configuration folder.
    """
    platform = get_platform()
    folder_name = "blender"
    parent_folder_name = "Blender Foundation"

    if custom_folder:
        folder_name = custom_folder
        parent_folder_name = custom_folder

    if platform == "Windows":
        return Path(os.getenv("APPDATA"), parent_folder_name, folder_name)
    elif platform == "Linux":
        return Path(os.path.expanduser("~/.config"), folder_name)
    elif platform == "macOS":
        return Path(os.path.expanduser("~/Library/Application Support"), folder_name)
