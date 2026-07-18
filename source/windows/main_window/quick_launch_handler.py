from __future__ import annotations

from typing import TYPE_CHECKING

from i18n import t
from modules.settings import (
    add_quick_launch_path,
    remove_quick_launch_path,
)
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget
from windows.popup_window import Popup

if TYPE_CHECKING:
    from widgets.library_widget import LibraryWidget

    from .window import BlenderLauncher


class QuickLaunchHandler(QObject):
    quick_launch_fail_signal = Signal()
    builds_changed = Signal()

    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent)
        self.launcher: BlenderLauncher = parent
        self.quick_launch_builds: list[LibraryWidget] = []
        self.quick_launch_fail_signal.connect(self.quick_launch_fail)

    @Slot()
    def on_activate_quick_launch(self):
        if self.launcher.settings_window is None:
            self.quick_launch()

    def is_quick_launch_path(self, path: str) -> bool:
        return any(w.link.as_posix() == path for w in self.quick_launch_builds)

    @Slot(QWidget)
    def add_quick_launch_build(self, w: LibraryWidget):
        path = w.link.as_posix()
        if self.is_quick_launch_path(path):
            return

        self.quick_launch_builds.append(w)
        add_quick_launch_path(path)
        self.builds_changed.emit()

    @Slot(QWidget)
    def remove_quick_launch_build(self, w: LibraryWidget):
        path = w.link.as_posix()
        matches = [b for b in self.quick_launch_builds if b.link.as_posix() == path]
        if not matches:
            return

        for b in matches:
            self.quick_launch_builds.remove(b)
            b.remove_from_quick_launch()

        remove_quick_launch_path(path)
        self.builds_changed.emit()

    def forget_quick_launch_build(self, w: LibraryWidget):
        if w in self.quick_launch_builds:
            self.quick_launch_builds.remove(w)
            remove_quick_launch_path(w.link.as_posix())
            self.builds_changed.emit()

    def reset(self):
        self.quick_launch_builds.clear()
        self.builds_changed.emit()

    def quick_launch(self, build: LibraryWidget | None = None):
        try:
            target = build if build is not None else next(iter(self.quick_launch_builds), None)
            assert target is not None
            target.launch()
        except Exception:
            self.quick_launch_fail_signal.emit()

    def quick_launch_fail(self):
        self.dlg = Popup.setup(
            parent=self.launcher,
            message=t("msg.popup.quick_launch_tray"),
            buttons=Popup.Button.info(),
        )
