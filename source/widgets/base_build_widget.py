import abc
import re
import webbrowser

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QWidget
from widgets.base_menu_widget import BaseMenuWidget


class BaseBuildWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.menu = BaseMenuWidget(parent=self)
        self.menu.setFont(self.parent.font_10)

        self.showReleaseNotesAction = QAction("Show Release Notes")
        self.showReleaseNotesAction.triggered.connect(self.show_release_notes)

    @abc.abstractmethod
    def context_menu(self):
        pass

    @QtCore.pyqtSlot()
    def show_release_notes(self):
        if self.build_info.branch == "stable":
            # TODO Check format for Blender 3 release
            # Extract X.X format version
            ver = self.build_info.semversion
            webbrowser.open(f"https://wiki.blender.org/wiki/Reference/Release_Notes/{ver.major}.{ver.minor}")
        elif self.build_info.branch == "lts":
            # Raw numbers from version
            v = re.sub(r"\D", "", str(self.build_info.semversion.finalize_version()))

            webbrowser.open(f"https://www.blender.org/download/lts/#lts-release-{v}")
        else:  # Open for builds with D12345 name pattern
            # Extract only D12345 substring
            m = re.search(r"D\d{5}", self.build_info.branch)

            webbrowser.open(f"https://developer.blender.org/{m.group(0)}")
