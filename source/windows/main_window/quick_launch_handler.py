from i18n import t
from modules.settings import (
    get_favorite_path,
    set_favorite_path,
)
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget
from widgets.library_widget import LibraryWidget
from windows.popup_window import Popup


class QuickLaunchHandler(QObject):
    quick_launch_fail_signal = Signal()
    """
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.quick_launch_build = None
        self.quick_launch_fail_signal.connect(self.quick_launch_fail)

    @Slot()
    def on_activate_quick_launch(self):
        if self.parent().settings_window is None: # type: ignore
            self.quick_launch()

    @Slot(QWidget)
    def set_quick_launch_build(self, w: LibraryWidget):
        self.remove_quick_launch()
        if w.link.as_posix() != get_favorite_path():
            set_favorite_path(w.link.as_posix())
        self.quick_launch_build = w

    @Slot()
    def remove_quick_launch(self):
        if self.quick_launch_build is not None:
            self.quick_launch_build.remove_from_quick_launch()
        self.quick_launch_build = None

    def quick_launch(self):
        try:
            assert self.quick_launch_build
            self.quick_launch_build.launch()
        except Exception:
            self.quick_launch_fail_signal.emit()

    def quick_launch_fail(self):
        self.dlg = Popup.setup(
            parent=self.parent,
            message=t("msg.popup.quick_launch_tray"),
            buttons=Popup.Button.info(),
        )
