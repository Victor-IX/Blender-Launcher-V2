from __future__ import annotations

import gettext
import logging
import logging.handlers
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import NoReturn

import modules._resources_rc
from modules import argument_parsing as ap
from modules._platform import _popen, get_cache_path, get_cwd, get_launcher_name, get_platform, is_frozen
from modules.cli_launching import cli_launch
from modules.shortcut import register_windows_filetypes, unregister_windows_filetypes
from modules.version_matcher import VALID_FULL_QUERIES, VALID_QUERIES, VERSION_SEARCH_SYNTAX
from PySide6.QtWidgets import QApplication
from semver import Version
from windows.popup_window import PopupWindow, PopupIcon

LOG_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[37m",  # White
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
}

RESET_COLOR = "\033[0m"  # Reset to default color


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, RESET_COLOR)
        message = super().format(record)
        return f"{log_color}{message}{RESET_COLOR}"


version = Version(
    2,
    4,
    0,
    prerelease="rc.3",
)

_ = gettext.gettext

# Setup logging config
_format = "[%(asctime)s:%(levelname)s] %(message)s"
cache_path = Path(get_cache_path())
if not cache_path.is_dir():
    cache_path.mkdir()
color_formatter = ColoredFormatter(_format)

file_handler = logging.handlers.RotatingFileHandler(
    cache_path.absolute() / "Blender Launcher.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=2,
)
file_handler.setFormatter(logging.Formatter(_format))
file_handler.doRollover()

stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setFormatter(color_formatter)

logging.basicConfig(
    format=_format,
    handlers=[file_handler, stream_handler],
)

logger = logging.getLogger(__name__)


# Setup exception handling
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error(f"{get_platform()} - Blender Launcher {version}", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


def add_help(parser: ArgumentParser):
    parser.add_argument(
        parser.prefix_chars + "h",
        parser.prefix_chars * 2 + "help",
        action="store_true",
        help="show this help message and exit",
    )


def main():
    parser = ArgumentParser(description=f"Blender Launcher V2 ({version})", add_help=False)
    add_help(parser)

    subparsers = parser.add_subparsers(dest="command")

    update_parser = subparsers.add_parser(
        "update",
        help="Update the application to a new version.",
        add_help=False,
    )
    add_help(update_parser)
    update_parser.add_argument("version", help="Version to update to.", nargs="?")

    parser.add_argument("-d", "-debug", "--debug", help="Enable debug logging.", action="store_true")
    parser.add_argument("-set-library-folder", help="Set library folder", type=Path)
    parser.add_argument("-force-first-time", help="Force the first time setup", action="store_true")
    parser.add_argument(
        "--offline",
        "-offline",
        help="Run the application offline. (Disables scraper threads and update checks)",
        action="store_true",
    )
    parser.add_argument(
        "--build-cache",
        help="Launch the app and cache all the available builds.",
        action="store_true",
    )
    parser.add_argument(
        "--instanced",
        "-instanced",
        help="Do not check for existing instance.",
        action="store_true",
    )

    launch_parser = subparsers.add_parser(
        "launch",
        help="Launch a specific version of Blender. If not file or version is specified, Quick launch is chosen.",
        add_help=False,
    )
    add_help(launch_parser)
    grp = launch_parser.add_mutually_exclusive_group()
    grp.add_argument("-f", "--file", type=Path, help="Path to a specific Blender file to launch.")
    grp.add_argument(
        "-ol", "--open-last", action="store_true", help="Open the last file in the specified blender build"
    )

    launch_parser.add_argument("-v", "--version", help=f"Version to launch. {VERSION_SEARCH_SYNTAX}")
    launch_parser.add_argument(
        "-c",
        "--cli",
        action="store_true",
        help="Launch Blender from CLI. does not open any QT frontend. WARNING: LIKELY DOES NOT WORK IN WINDOWS BUNDLED EXECUTABLE",
    )

    if sys.platform == "win32":
        subparsers.add_parser(
            "register",
            help="Registers the program to read .blend builds. Adds Blender Launcher to the Open With window. (WIN ONLY)",
        )
        subparsers.add_parser("unregister", help="Undoes the changes that `register` makes. (WIN ONLY)")

    input_args = None

    # Shortcut for launching
    small_parser = ArgumentParser(add_help=False)
    small_parser.add_argument("file", nargs="?", type=Path)
    args, argv = small_parser.parse_known_args()
    if args.file is not None and args.file.exists():
        input_args = ["launch", "-f", str(args.file)]

    args, argv = parser.parse_known_args(input_args)

    if argv:
        msg = _("unrecognized arguments: ") + " ".join(argv)
        ap.error(parser, msg)

    # Custom help is necessary for frozen Windows builds
    if args.help:
        ap.show_help(parser, update_parser, launch_parser, args)
        sys.exit(0)

    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    # Log Blender Launcher version
    logger.info(f"Blender Launcher Version: {version}")

    # Create an instance of application and set its core properties
    app = QApplication(["blender-launcher-v2"])
    app.setApplicationName("blender-launcher-v2")
    app.setStyle("Fusion")
    app.setApplicationVersion(str(version))

    set_lib_folder: Path | None = args.set_library_folder
    if set_lib_folder is not None:
        start_set_library_folder(app, str(set_lib_folder))

    if args.command == "update":
        start_update(app, args.instanced, args.version)

    if args.command == "launch":
        start_launch(app, args.file, args.version, args.open_last, cli=args.cli)

    if args.command == "register":
        start_register()
    if args.command == "unregister":
        start_unregister()

    if not args.instanced:
        check_for_instance()

    from windows.main_window import BlenderLauncher

    app.setQuitOnLastWindowClosed(False)

    BlenderLauncher(app=app, version=version, offline=args.offline, build_cache=args.build_cache, force_first_time=args.force_first_time)
    sys.exit(app.exec())


def start_set_library_folder(app: QApplication, lib_folder: str):
    from modules.settings import set_library_folder

    if set_library_folder(str(lib_folder)):
        logging.info(f"Library folder set to {lib_folder!s}")
    else:
        logging.error("Failed to set library folder")
        PopupWindow(
            title="Warning",
            message="Passed path is not a valid folder or<br>it doesn't have write permissions!",
            icon=PopupIcon.WARNING,
            button="Quit",
            app=app,
        ).show()
        sys.exit(app.exec())


def start_update(app: QApplication, is_instanced: bool, tag: str | None):
    import shutil

    from windows.update_window import BlenderLauncherUpdater

    if is_instanced or not is_frozen():
        BlenderLauncherUpdater(app=app, version=version, release_tag=tag)
        sys.exit(app.exec())
    else:
        # Copy the launcher to the updater position
        bl_exe, blu_exe = get_launcher_name()
        cwd = get_cwd()
        source = cwd / bl_exe
        dist = cwd / blu_exe
        shutil.copy(source, dist)

        # Run the updater with the instanced flag
        if get_platform() == "Windows":
            _popen([blu_exe, "--instanced", "update"])
        elif get_platform() == "Linux":
            os.chmod(blu_exe, 0o744)
            _popen(f'nohup "{blu_exe}" --instanced update')
        sys.exit(0)


def start_launch(
    app: QApplication,
    file: Path | None = None,
    version_query: str | None = None,
    open_last: bool = False,
    cli: bool = False,
) -> NoReturn:
    from modules.version_matcher import VersionSearchQuery
    from windows.launching_window import LaunchingWindow

    # convert version_query to VersionSearchQuery
    if version_query is not None:
        try:
            query = VersionSearchQuery.parse(version_query)
        except Exception:
            print("Failed to parse query")
            print(VERSION_SEARCH_SYNTAX)
            print("Valid version queries include: ")
            print(VALID_FULL_QUERIES)
            sys.exit(1)
    else:
        query = None

    # remove quotes around file path if they exist
    if file is not None:
        file = Path(str(file).strip('"'))

    if cli:
        cli_launch(file=file, version_query=query, open_last=open_last)
        sys.exit(1)
    else:
        LaunchingWindow(app, version_query=query, blendfile=file, open_last=open_last).show()
        sys.exit(app.exec())


def start_register():
    import sys

    register_windows_filetypes()

    sys.exit(0)


def start_unregister():
    import sys

    unregister_windows_filetypes()
    sys.exit(0)


def check_for_instance():
    from PySide6.QtCore import QByteArray
    from PySide6.QtNetwork import QLocalSocket

    socket = QLocalSocket()
    socket.connectToServer("blender-launcher-server")
    is_running = socket.waitForConnected()
    if is_running:
        socket.write(QByteArray(str(version).encode()))
        socket.waitForBytesWritten()
        socket.close()
        sys.exit()


if __name__ == "__main__":
    main()
