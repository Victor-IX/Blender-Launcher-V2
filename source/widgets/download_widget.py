from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from modules.build_info import BuildInfo, ReadBuildTask, parse_blender_ver
from modules.enums import MessageType
from modules.settings import get_install_template, get_library_folder
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from semver import Version
from threads.downloader import DownloadTask
from threads.extractor import ExtractTask
from threads.renamer import RenameTask
from threads.template_installer import TemplateTask
from widgets.base_build_widget import BaseBuildWidget
from widgets.base_progress_bar_widget import BaseProgressBarWidget
from widgets.build_state_widget import BuildStateWidget
from widgets.datetime_widget import DateTimeWidget
from widgets.elided_text_label import ElidedTextLabel

if TYPE_CHECKING:
    from widgets.base_page_widget import BasePageWidget
    from widgets.library_widget import LibraryWidget
    from windows.main_window import BlenderLauncher


class DownloadState(Enum):
    IDLE = 1
    DOWNLOADING = 2
    EXTRACTING = 3
    READING = 4
    RENAMING = 5


class DownloadWidget(BaseBuildWidget):
    focus_installed_widget = Signal(BaseBuildWidget)

    def __init__(self, parent: BlenderLauncher, list_widget, item, build_info, installed, show_new=False):
        super().__init__(parent=parent)
        self.parent: BlenderLauncher = parent
        self.list_widget = list_widget
        self.item = item
        self.build_info: BuildInfo = build_info
        self.show_new = show_new
        self.installed: LibraryWidget | None = None
        self.state = DownloadState.IDLE
        self.build_dir = None
        self.source_file = None

        self.progressBar = BaseProgressBarWidget()
        self.progressBar.setFont(self.parent.font_8)
        self.progressBar.setFixedHeight(18)
        self.progressBar.hide()

        self.downloadButton = QPushButton("Download")
        self.downloadButton.setFixedWidth(85)
        self.downloadButton.setProperty("LaunchButton", True)
        self.downloadButton.clicked.connect(self.init_downloader)
        self.downloadButton.setCursor(Qt.CursorShape.PointingHandCursor)

        self.installedButton = QPushButton("Installed")
        self.installedButton.setFixedWidth(85)
        self.installedButton.setProperty("InstalledButton", True)
        self.installedButton.clicked.connect(self.focus_installed)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setFixedWidth(85)
        self.cancelButton.setProperty("CancelButton", True)
        self.cancelButton.clicked.connect(self.download_cancelled)
        self.cancelButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancelButton.hide()

        self.main_hl = QHBoxLayout(self)
        self.main_hl.setContentsMargins(2, 2, 0, 2)
        self.main_hl.setSpacing(0)

        self.sub_vl = QVBoxLayout()
        self.sub_vl.setContentsMargins(0, 0, 0, 0)
        self.main_hl.setSpacing(0)

        self.build_info_hl = QHBoxLayout()
        self.build_info_hl.setContentsMargins(0, 0, 0, 0)
        self.main_hl.setSpacing(0)

        self.progress_bar_hl = QHBoxLayout()
        self.progress_bar_hl.setContentsMargins(16, 0, 8, 0)
        self.main_hl.setSpacing(0)

        self.subversionLabel = QLabel(self.build_info.display_version)
        self.subversionLabel.setFixedWidth(85)
        self.subversionLabel.setIndent(20)
        self.subversionLabel.setToolTip(str(self.build_info.semversion))

        self.branchLabel = ElidedTextLabel(self.build_info.display_label, self)
        self.commitTimeLabel = DateTimeWidget(self.build_info.commit_time, self.build_info.build_hash, self)
        self.build_state_widget = BuildStateWidget(parent.icons, self)

        self.build_info_hl.addWidget(self.subversionLabel)
        self.build_info_hl.addWidget(self.branchLabel, stretch=1)
        self.build_info_hl.addWidget(self.commitTimeLabel)

        if self.show_new and not self.installed:
            self.build_state_widget.setNewBuild(True)

        self.progress_bar_hl.addWidget(self.progressBar)

        self.sub_vl.addLayout(self.build_info_hl)
        self.sub_vl.addLayout(self.progress_bar_hl)

        self.main_hl.addWidget(self.downloadButton)
        self.main_hl.addWidget(self.cancelButton)
        self.main_hl.addWidget(self.installedButton)
        self.main_hl.addLayout(self.sub_vl)
        self.main_hl.addWidget(self.build_state_widget)

        if installed:
            self.setInstalled(installed)
        else:
            self.installedButton.hide()

        if self.build_info.branch in {"stable", "lts", "daily", "bforartists"}:
            self.menu.addAction(self.showReleaseNotesAction)
        else:
            regexp = re.compile(r"D\d{5}")

            if regexp.search(self.build_info.branch):
                self.showReleaseNotesAction.setText("Show Patch Details")
                self.menu.addAction(self.showReleaseNotesAction)

        self.list_widget.sortItems()

    def context_menu(self):
        if self.installed:
            self.installed.context_menu()
            return

        self.menu.trigger()

    def mouseDoubleClickEvent(self, _event):
        if self.state != DownloadState.DOWNLOADING and not self.installed:
            self.init_downloader()
        elif self.installed:
            self.focus_installed()

    @Slot()
    def focus_installed(self):
        self.focus_installed_widget.emit(self.installed)

    def mouseReleaseEvent(self, _event):
        if self.show_new is True:
            self.build_state_widget.setNewBuild(False)
            self.show_new = False

    def init_downloader(self):
        self.item.setSelected(True)

        if self.show_new is True:
            self.build_state_widget.setNewBuild(False)
            self.show_new = False

        assert self.parent.manager is not None
        self.set_state(DownloadState.DOWNLOADING)
        self.dl_task = DownloadTask(
            manager=self.parent.manager,
            link=self.build_info.link,
        )
        self.dl_task.progress.connect(self.progressBar.set_progress)
        self.dl_task.finished.connect(self.init_extractor)
        self.parent.task_queue.append(self.dl_task)

    def set_state(self, state: DownloadState):
        self.state = state
        if state == DownloadState.IDLE:
            self.progressBar.hide()
            self.cancelButton.hide()
            self.build_state_widget.setDownload(False)
            self.build_state_widget.setExtract(False)
        if state == DownloadState.DOWNLOADING:
            self.progressBar.set_title("Downloading")
            self.progressBar.show()
            self.cancelButton.show()
            self.cancelButton.setEnabled(True)
            self.downloadButton.hide()
            self.build_state_widget.setDownload()
        elif state == DownloadState.EXTRACTING:
            self.progressBar.show()
            self.progressBar.set_title("Extracting")
            self.cancelButton.setEnabled(False)
            self.build_state_widget.setExtract()
        elif state == DownloadState.READING:
            self.progressBar.show()
        # elif state == DownloadState.RENAMING:

    def init_extractor(self, source):
        self.set_state(DownloadState.EXTRACTING)

        library_folder = Path(get_library_folder())

        if self.build_info.branch in ("stable", "lts"):
            dist = library_folder / "stable"
        elif self.build_info.branch == "daily":
            dist = library_folder / "daily"
        elif self.build_info.branch == "bforartists":
            dist = library_folder / "bforartists"
        else:
            dist = library_folder / "experimental"

        self.source_file = source
        t = ExtractTask(file=source, destination=dist)
        t.progress.connect(self.progressBar.set_progress)
        t.finished.connect(self.init_template_installer)
        self.parent.task_queue.append(t)

    def init_template_installer(self, dist: Path):
        self.build_state_widget.setExtract(False)
        self.build_dir = dist

        if get_install_template():
            self.progressBar.set_title("Copying data...")
            t = TemplateTask(destination=self.build_dir)
            t.finished.connect(self.download_get_info)
            self.parent.task_queue.append(t)
        else:
            self.download_get_info()

    def download_cancelled(self):
        self.item.setSelected(True)
        self.set_state(DownloadState.IDLE)
        self.cancelButton.hide()
        self.downloadButton.show()
        self.parent.task_queue.remove_task(self.dl_task)
        self.build_state_widget.setDownload(False)

    def download_get_info(self):
        self.set_state(DownloadState.READING)
        if self.parent.platform == "Linux":
            archive_name = Path(self.build_info.link).with_suffix("").stem
        else:
            archive_name = Path(self.build_info.link).stem

        assert self.build_dir is not None

        # If the returned version from the executable is invalid it might break loading.
        ver_ = parse_blender_ver(self.build_dir.name, search=True)
        ver = Version(
            ver_.major,
            ver_.minor,
            ver_.patch,
            prerelease=ver_.prerelease,
        )

        t = ReadBuildTask(
            self.build_dir,
            info=BuildInfo(
                str(self.build_dir),
                subversion=str(ver),
                build_hash=None,
                commit_time=self.build_info.commit_time,
                branch=self.build_info.branch,
                custom_executable=self.build_info.custom_executable,
            ),
            archive_name=archive_name,
        )
        t.finished.connect(self.download_rename)
        t.failure.connect(lambda: print("Reading failed"))
        self.parent.task_queue.append(t)

    def download_rename(self, build_info: BuildInfo):
        self.set_state(DownloadState.RENAMING)
        new_name = f"blender-{build_info.full_semversion}"
        assert self.build_dir is not None
        t = RenameTask(
            src=self.build_dir,
            dst_name=new_name,
        )
        t.finished.connect(self.download_finished)
        t.failure.connect(lambda: print("Renaming failed"))
        self.parent.task_queue.append(t)

    def download_finished(self, path):
        self.set_state(DownloadState.IDLE)

        if path is None:
            path = self.build_dir

        if path is not None:
            widget = self.parent.draw_to_library(path, True)

            assert self.source_file is not None
            self.parent.clear_temp(self.source_file)

            if self.build_info.branch == "bforartists":
                message = f"Bforartists {self.subversionLabel.text()} {self.build_info.commit_time}"
            else:
                name = f"{self.subversionLabel.text()} {self.branchLabel.text} {self.build_info.commit_time}"
                message = f"Blender {name}"
            message += " download finished!"

            self.parent.show_message(
                message,
                message_type=MessageType.DOWNLOADFINISHED,
            )
            self.setInstalled(widget)

    def setInstalled(self, build_widget: BaseBuildWidget):
        if self.state == DownloadState.IDLE:
            build_widget.destroyed.connect(self.uninstalled)
            self.downloadButton.hide()
            self.installedButton.show()
            self.cancelButton.hide()
            self.progressBar.hide()
            self.installed = build_widget

    @Slot()
    def uninstalled(self):
        self.installedButton.hide()
        self.downloadButton.show()
        self.installed = None
