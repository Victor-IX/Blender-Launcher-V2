import os
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QAction, QApplication, QHBoxLayout, QLabel, QPushButton
from widgets.base_build_widget import BaseBuildWidget
from widgets.base_line_edit import BaseLineEdit
from widgets.base_menu_widget import BaseMenuWidget
from widgets.build_state_widget import BuildStateWidget
from widgets.datetime_widget import DateTimeWidget
from widgets.elided_text_label import ElidedTextLabel
from widgets.left_icon_button_widget import LeftIconButtonWidget
from windows.dialog_window import DialogWindow

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class PreferenceFactoryWidget(BaseBuildWidget):
    def __init__(self, parent, list_widget):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)

        self.list_widget = list_widget

        # box should highlight when dragged over
        self.layout: QHBoxLayout = QHBoxLayout()
        self.layout.setContentsMargins(2, 2, 0, 2)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.layout)
        self.draw()

    def draw(self):
        self.installButton = QPushButton("Create...")
        self.installButton.setFixedWidth(85)
        self.installButton.setProperty("CreateButton", True)

        self.subversionLabel = QLabel()
        self.subversionLabel.setFixedWidth(85)
        self.subversionLabel.setIndent(20)

        self.layout.addWidget(self.installButton)
        self.layout.addWidget(self.subversionLabel)

        self.installButton.clicked.connect(self.install)
        self.installButton.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button == Qt.MouseButton.LeftButton:
            mod = QApplication.keyboardModifiers()
            if mod not in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier):
                self.list_widget.clearSelection()

            event.accept()
        event.ignore()

    @pyqtSlot()
    def install(self):
        ...

    @QtCore.pyqtSlot()
    def ask_remove_from_drive(self):
        self.dlg = DialogWindow(
            parent=self,
            title="Warning",
            text="Are you sure you want to<br> \
                  delete these preferences?<br> \
                  Any blender version using these will<br> \
                  automatically create a new one.",
            accept_text="Yes",
            cancel_text="No",
        )

        if len(self.list_widget.selectedItems()) > 1:
            self.dlg.accepted.connect(self.remove_from_drive_extended)
        else:
            self.dlg.accepted.connect(self.remove_from_drive)
