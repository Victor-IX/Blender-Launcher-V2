import abc
import re
import webbrowser
import logging

from pathlib import PurePosixPath

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget
from threads.scraper import BFA_NC_WEBDAV_SHARE_TOKEN, BFA_NC_WEBDAV_URL, get_bfa_nc_https_download_url
from webdav4.client import Client
from widgets.base_menu_widget import BaseMenuWidget

logger = logging.getLogger()


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

    @QtCore.Slot()
    def show_release_notes(self):
        branch = self.build_info.branch

        if branch in {"stable", "daily"}:
            ver = self.build_info.semversion
            webbrowser.open(f"https://wiki.blender.org/wiki/Reference/Release_Notes/{ver.major}.{ver.minor}")
        elif branch == "lts":
            # Raw numbers from version
            v = re.sub(r"\D", "", str(self.build_info.semversion.finalize_version()))

            webbrowser.open(f"https://www.blender.org/download/lts/#lts-release-{v}")
        elif self.build_info.branch == "bforartists":
            ver = self.build_info.semversion
            client = Client(BFA_NC_WEBDAV_URL, auth=(BFA_NC_WEBDAV_SHARE_TOKEN, ""))
            try:
                entries = client.ls(
                    f"/Bforartists {ver.major}.{ver.minor}.{ver.patch}", detail=True, allow_listing_resource=True
                )
                for e in entries:
                    path = PurePosixPath(e["name"])
                    if "releasenote" in path.name.lower():
                        webbrowser.open(get_bfa_nc_https_download_url(path))
            except Exception:
                logger.exception("Failed get Bforartists release note")
        else:
            # Open for builds with D12345 name pattern
            # Extract only D12345 substring
            m = re.search(r"D\d{5}", branch)
            if m is not None:
                webbrowser.open(f"https://developer.blender.org/{m.group(0)}")

            # Open for builds with pr123456 name pattern
            # Extract only 123456 substring
            if branch == "patch":
                m = re.search(r"pr(\d+)", self.build_info.subversion, flags=re.IGNORECASE)
            else:
                m = re.search(r"pr(\d+)", self.build_info.branch, flags=re.IGNORECASE)
            if m is not None:
                webbrowser.open(f"https://projects.blender.org/blender/blender/pulls/{m.group(1)}")
