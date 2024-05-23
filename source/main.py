from __future__ import annotations

import gettext
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

import modules._resources_rc
from modules import argument_parsing as ap
from modules._platform import _popen, get_cache_path, get_cwd, get_launcher_name, get_platform, is_frozen
from PyQt5.QtWidgets import QApplication
from semver import Version
from windows.dialog_window import DialogWindow

version = Version(
    2,
    2,
    0,
    prerelease="rc.2",
)

_ = gettext.gettext

# Setup logging config
_format = "[%(asctime)s:%(levelname)s] %(message)s"
cache_path = Path(get_cache_path())
if not cache_path.is_dir():
    cache_path.mkdir()
logging.basicConfig(
    format=_format,
    handlers=[
        logging.FileHandler(cache_path.absolute() / "Blender Launcher.log"),
        logging.StreamHandler(stream=sys.stdout),
    ],
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

    update_parser = subparsers.add_parser("update", help="Update the application to a new version.", add_help=False)
    add_help(update_parser)
    update_parser.add_argument("version", help="Version to update to.", nargs="?")

    parser.add_argument("-debug", help="Enable debug logging.", action="store_true")
    parser.add_argument("-set-library-folder", help="Set library folder", type=Path)
    parser.add_argument(
        "--offline",
        "-offline",
        help="Run the application offline. (Disables scraper threads and update checks)",
        action="store_true",
    )
    parser.add_argument(
        "--instanced",
        "-instanced",
        help="Do not check for existing instance.",
        action="store_true",
    )

    # possible launch_parser
    # args:
    #   "launch":               Launch a specific version of Blender. If no file or version is specified,
    #                            the favorite build is chosen. If there is no favorite build, TODO: BUILD_CHOOSER
    #   "-f" | "--file":        Path to a specific Blender file to launch.
    #   "-v" | "--version":     Version to launch. If not specified, the latest stable release is used.

    args, argv = parser.parse_known_args()
    if argv:
        msg = _("unrecognized arguments: ") + " ".join(argv)
        ap.error(parser, msg)

    # Custom help is necessary for frozen Windows builds
    if args.help:
        ap.show_help(parser, update_parser, args)
        sys.exit(0)

    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    # Create an instance of application and set its core properties
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationVersion(str(version))

    set_lib_folder: Path | None = args.set_library_folder
    if set_lib_folder is not None:
        start_set_library_folder(app, str(set_lib_folder))

    if args.command == "update":
        start_update(app, args.instanced, args.version)

    # if args.command == "launch":
    #     ...

    if not args.instanced:
        check_for_instance()

    from windows.main_window import BlenderLauncher

    app.setQuitOnLastWindowClosed(False)

    BlenderLauncher(app=app, version=version, offline=args.offline)
    sys.exit(app.exec())


def start_set_library_folder(app: QApplication, lib_folder: str):
    from modules.settings import set_library_folder

    if set_library_folder(str(lib_folder)):
        logging.info(f"Library folder set to {lib_folder!s}")
    else:
        logging.error("Failed to set library folder")
        dlg = DialogWindow(
            title="Warning",
            text="Passed path is not a valid folder or<br>it doesn't have write permissions!",
            accept_text="Quit",
            cancel_text=None,
            app=app,
        )
        dlg.show()
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


def check_for_instance():
    from PyQt5.QtCore import QByteArray
    from PyQt5.QtNetwork import QLocalSocket

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
