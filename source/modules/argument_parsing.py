import sys
from argparse import ArgumentParser, Namespace

from i18n import t
from modules.platform_utils import is_frozen, show_windows_help

# These custom handlings are necessary for frozen Windows builds to show
# argparse help messages properly


def error(parser: ArgumentParser, msg: str):
    if is_frozen() and sys.platform == "win32":
        from PySide6.QtWidgets import QApplication
        from windows.popup_window import Popup

        app = QApplication([])
        Popup.error(
            message=t("msg.err.argparse", args=parser.format_usage(), err=msg),
            buttons=Popup.Button.QUIT,
            app=app,
        ).show()
        sys.exit(app.exec())
    else:
        parser.error(msg)


def show_help(
    parser: ArgumentParser,
    update_parser: ArgumentParser | None,
    launch_parser: ArgumentParser,
    args: Namespace,
):
    if is_frozen() and sys.platform == "win32":
        if args.command == "update":
            assert update_parser is not None
            show_windows_help(update_parser)
        elif args.command == "launch":
            show_windows_help(launch_parser)
        else:
            show_windows_help(parser)
    else:
        if args.command == "update":
            if update_parser is None:
                print("Update command called while in a contained environment. Please use your package manager's update functions.")
                sys.exit(1)
            update_parser.print_help()
        elif args.command == "launch":
            launch_parser.print_help()
        else:
            parser.print_help()
