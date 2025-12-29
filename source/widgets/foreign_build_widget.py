from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from modules.build_info import BuildInfo
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout
from widgets.base_build_widget import BaseBuildWidget
from widgets.elided_text_label import ElidedTextLabel
from windows.custom_build_dialog_window import CustomBuildDialogWindow

from .base_list_widget import BaseListWidget

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class UnrecoBuildWidget(BaseBuildWidget):
    def __init__(self, parent: "BlenderLauncher", path: Path, list_widget: BaseListWidget, item):
        super().__init__(parent=parent)
        self.parent: BlenderLauncher = parent
        self.path = path
        self.list_widget = list_widget
        self.item = item
        self.build_info = BuildInfo(
            str(path),
            "0.0.0",
            "",
            datetime.now(tz=UTC),
            path.parent.name,
            str(path.name),
            False,
            None,
        )

        self.init_button = QPushButton("Initialize")
        self.init_button.setFixedWidth(85)
        self.init_button.setProperty("CreateButton", True)
        self.init_button.clicked.connect(self.init_unrecognized)
        self.init_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.filename = ElidedTextLabel(str(path.name))

        self.main_hl = QHBoxLayout()
        self.main_hl.setContentsMargins(2, 2, 0, 2)
        self.main_hl.setSpacing(0)

        self.sub_vl = QVBoxLayout()
        self.sub_vl.setContentsMargins(16, 0, 8, 0)
        self.sub_vl.addWidget(self.filename, stretch=1)

        self.main_hl.addWidget(self.init_button)
        self.main_hl.addLayout(self.sub_vl)

        self.setLayout(self.main_hl)

    def init_unrecognized(self):
        dlg = CustomBuildDialogWindow(self.parent, self.path)
        dlg.accepted.connect(self.new_build)

    @Slot(BuildInfo)
    def new_build(self, binfo: BuildInfo):
        binfo.write_to(self.path)
        self.parent.draw_to_library(self.path, True)
        self.destroy()

    def context_menu(self):
        self.menu.trigger()

    def mouseDoubleClickEvent(self, event):
        self.init_unrecognized()
        event.accept()

    def destroy(self):
        self.list_widget.remove_item(self.item)
        super().destroy()
