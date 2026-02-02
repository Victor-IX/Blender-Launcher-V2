from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from modules.build_info import BuildInfo
from modules.settings import get_library_folder
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from threads.remover import RemovalTask
from widgets.base_build_widget import BaseBuildWidget
from widgets.left_icon_button_widget import LeftIconButtonWidget
from windows.popup_window import PopupButton, PopupIcon, PopupWindow

if TYPE_CHECKING:
    from items.base_list_widget_item import BaseListWidgetItem
    from windows.main_window import BlenderLauncher

logger = logging.getLogger()


class LibraryDamagedWidget(BaseBuildWidget):
    def __init__(
        self,
        parent: BlenderLauncher,
        item: BaseListWidgetItem,
        link,
        list_widget,
    ):
        super().__init__(
            parent=parent,
            item=item,
            build_info=BuildInfo.from_blender_path(link),
        )
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        self.parent: BlenderLauncher = parent
        self.link = Path(link)
        self.list_widget = list_widget

        self.outer_layout = QHBoxLayout()
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)

        # box should highlight when dragged over
        self.layout_widget = QWidget(self)
        self.lay: QHBoxLayout = QHBoxLayout()
        self.lay.setContentsMargins(2, 2, 0, 2)
        self.lay.setSpacing(0)
        self.layout_widget.setLayout(self.lay)
        self.outer_layout.addWidget(self.layout_widget)
        self.setLayout(self.outer_layout)

        self.infoLabel = QLabel(f"Build *{self.link.name}* is damaged!")
        self.infoLabel.setWordWrap(True)
        self.launchButton = LeftIconButtonWidget("Delete", parent=self)
        self.launchButton.setFixedWidth(95)
        self.launchButton.setProperty("CancelButton", True)
        self.launchButton.clicked.connect(self.ask_remove_from_drive)

        self.lay.addWidget(self.launchButton)
        self.lay.addWidget(self.infoLabel, stretch=1)

    @Slot()
    def ask_remove_from_drive(self):
        self.item.setSelected(True)
        self.dlg = PopupWindow(
            parent=self.parent,
            title="Warning",
            message="Do you want to delete, or<br>trash selected builds?",
            icon=PopupIcon.NONE,
            buttons=[PopupButton.DELETE, PopupButton.TRASH, PopupButton.CANCEL],
        )

        self.dlg.custom_signal.connect(self.removal_response)

    @Slot(PopupButton)
    def removal_response(self, s: PopupButton):
        if s != PopupButton.CANCEL:
            self.remove_from_drive(trash=(s == PopupButton.TRASH))

    @Slot()
    def remove_from_drive(self, trash=False):
        path = get_library_folder() / self.link
        a = RemovalTask(path, trash=trash)
        a.finished.connect(self.remover_completed)
        self.parent.task_queue.append(a)

        self.launchButton.set_text("Deleting")
        self.setEnabled(False)
        self.item.setFlags(self.item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

    def remover_completed(self, code):
        if code == 0:
            self.list_widget.remove_item(self.item)
        else:
            self.item.setFlags(self.item.flags() | Qt.ItemFlag.ItemIsSelectable)
