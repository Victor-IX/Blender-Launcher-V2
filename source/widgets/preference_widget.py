from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from modules.settings import get_library_folder
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from threads.remover import RemovalTask
from widgets.base_build_widget import BaseBuildWidget
from widgets.elided_text_label import ElidedTextLabel
from windows.dialog_window import DialogWindow

if TYPE_CHECKING:
    from modules.prefs_info import PreferenceInfo
    from widgets.base_list_widget import BaseListWidget
    from windows.main_window import BlenderLauncher


class PreferenceWidget(BaseBuildWidget):
    deleted = pyqtSignal()

    def __init__(self, info: PreferenceInfo, list_widget: BaseListWidget, parent: BlenderLauncher):
        super().__init__(parent)
        self.parent: BlenderLauncher
        self.list_widget = list_widget
        self.info = info

        self.layout: QHBoxLayout = QHBoxLayout()
        self.layout.setContentsMargins(2, 2, 0, 2)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.layout)

        self.draw()

    def draw(self):
        self.delete_button = QPushButton("Delete", self)
        self.delete_button.setFixedWidth(85)
        self.delete_button.setProperty("CancelButton", True)
        self.delete_button.clicked.connect(self.ask_remove_from_drive)
        self.target_ver_label = QLabel(str(self.info.target_version or ""), self)
        self.target_ver_label.setFixedWidth(100)
        self.target_ver_label.setIndent(20)
        self.name_label = ElidedTextLabel(self.info.name, self)

        self.layout.addWidget(self.delete_button)
        self.layout.addWidget(self.target_ver_label)
        self.layout.addWidget(self.name_label, stretch=1)

    @QtCore.pyqtSlot()
    def ask_remove_from_drive(self):
        self.dlg = DialogWindow(
            parent=self.parent,
            title="Warning",
            text="Are you sure you want to<br> \
                  delete these preferences?<br> \
                  Any blender version using these will<br> \
                  revert to the default.",
            accept_text="Yes",
            cancel_text="No",
        )

        self.dlg.accepted.connect(self.double_ask_remove_from_drive)

    @QtCore.pyqtSlot()
    def double_ask_remove_from_drive(self):
        self.dlg = DialogWindow(
            parent=self.parent,
            title="Warning",
            text="Are you ABSOLUTELY SURE?<br> \
                  This cannot be undone.<br>",
            accept_text="Yes",
            cancel_text="No",
        )

        if len(self.list_widget.selectedItems()) > 1:
            self.dlg.accepted.connect(self.remove_from_drive_extended)
        else:
            self.dlg.accepted.connect(self.remove_from_drive)


    @QtCore.pyqtSlot()
    def remove_from_drive_extended(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.itemWidget(item).remove_from_drive()


    @QtCore.pyqtSlot()
    def remove_from_drive(self):

        path = Path(get_library_folder()) / self.info.directory
        a = RemovalTask(path)
        a.finished.connect(self.remover_completed)
        self.parent.task_queue.append(a)


    @QtCore.pyqtSlot()
    def remover_completed(self):
        self.deleted.emit()
