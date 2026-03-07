import logging

from i18n import t
from modules.settings import (
    get_quick_launch_key_seq,
)
from PySide6.QtCore import QObject, Signal
from windows.popup_window import Popup

try:
    from pynput import keyboard

    HOTKEYS_AVAILABLE = True
except Exception as e:
    logging.exception(f"Error importing pynput: {e}\nGlobal hotkeys not supported.")
    HOTKEYS_AVAILABLE = False


class HotkeyHandler(QObject):
    """
    Manages the Global Hotkey functionality of Blender Launcher.

    This class holds a hotkey listener, which sends a signal to the main window to
    start the quick launch build.
    """

    hk_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__hk_listener = None

    def setup(self):
        if HOTKEYS_AVAILABLE:
            self.stop()
            key_seq = get_quick_launch_key_seq()
            keys = key_seq.split("+")

            for key in keys:
                if len(key) > 1:
                    key_seq = key_seq.replace(key, "<" + key + ">")

            try:
                self.__hk_listener = keyboard.GlobalHotKeys({key_seq: self.__trigger})
            except Exception:
                self.dlg = Popup.warning(
                    message=t("msg.popup.global_hotkeys_invalid"),
                    buttons=Popup.Button.info(),
                    parent=self.parent(),
                )
                return

            self.__hk_listener.start()

    def stop(self):
        if self.__hk_listener is not None:
            self.__hk_listener.stop()

    def __trigger(self):
        self.hk_triggered.emit()
