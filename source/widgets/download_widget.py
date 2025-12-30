from __future__ import annotations

import logging
import re
import shutil
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from modules.build_info import BuildInfo, ReadBuildTask, parse_blender_ver
from modules.enums import MessageType
from modules.settings import get_install_template, get_library_folder
from PySide6.QtCore import Qt, QTimer, Signal, Slot
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
from windows.popup_window import PopupIcon, PopupWindow

if TYPE_CHECKING:
    from widgets.base_page_widget import BasePageWidget
    from widgets.library_widget import LibraryWidget
    from windows.main_window import BlenderLauncher

logger = logging.getLogger()


class DownloadState(Enum):
    IDLE = 1
    DOWNLOADING = 2
    EXTRACTING = 3
    READING = 4
    RENAMING = 5


class DownloadWidget(BaseBuildWidget):
    focus_installed_widget = Signal(BaseBuildWidget)

    def __init__(self, parent: BlenderLauncher, list_widget, item, build_info, installed, show_new=False):
        super().__init__(
            parent=parent,
            item=item,
            build_info=build_info,
        )
        self.parent: BlenderLauncher = parent
        self.list_widget = list_widget
        self.show_new = show_new
        self.installed: LibraryWidget | None = None
        self.state = DownloadState.IDLE
        self.build_dir = None
        self.source_file = None
        self.updating_widget = None
        self._is_removed = False

        self.progressBar = BaseProgressBarWidget()
        self.progressBar.setFont(self.parent.font_8)
        self.progressBar.setFixedHeight(18)
        self.progressBar.hide()

        self.downloadButton = QPushButton("Download")
        self.downloadButton.setFixedWidth(95)  # Match header fakeLabel width
        self.downloadButton.setProperty("LaunchButton", True)
        self.downloadButton.clicked.connect(lambda: self.init_downloader())
        self.downloadButton.setCursor(Qt.CursorShape.PointingHandCursor)

        self.installedButton = QPushButton("Installed")
        self.installedButton.setFixedWidth(95)  # Match header fakeLabel width
        self.installedButton.setProperty("InstalledButton", True)
        self.installedButton.clicked.connect(self.focus_installed)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setFixedWidth(95)  # Match header fakeLabel width
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

        # Connect to column width changes from the page widget
        page_widget = self.list_widget.parent
        if page_widget is not None:
            page_widget.column_widths_changed.connect(self._update_column_widths)
            # Apply initial column widths
            widths = page_widget.get_column_widths()
            self._update_column_widths(widths[0], widths[1], widths[2])

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
            exp = re.compile(r"D\d{5}")

            if exp.search(self.build_info.branch):
                self.showReleaseNotesAction.setText("Show Patch Details")
                self.menu.addAction(self.showReleaseNotesAction)
            else:
                exp = re.compile(r"pr\d+", flags=re.IGNORECASE)
                if exp.search(self.build_info.subversion):
                    self.showReleaseNotesAction.setText("Show PR Details")
                    self.menu.addAction(self.showReleaseNotesAction)

        self.list_widget.sortItems()

    def context_menu(self) -> None:
        if self.installed:
            self.installed.context_menu()
            return

        self.menu.trigger()

    def mouseDoubleClickEvent(self, _event) -> None:
        if self.state != DownloadState.DOWNLOADING and not self.installed:
            self.init_downloader()
        elif self.installed:
            self.focus_installed()

    @Slot()
    def focus_installed(self) -> None:
        self.focus_installed_widget.emit(self.installed)

    def mouseReleaseEvent(self, _event) -> None:
        if self.show_new is True:
            self.build_state_widget.setNewBuild(False)
            self.show_new = False

    def init_downloader(self, updating_widget: LibraryWidget | None = None) -> None:
        self.item.setSelected(True)
        self.updating_widget = updating_widget

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

    def set_state(self, state: DownloadState) -> None:
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

    def init_extractor(self, source: Path) -> None:
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

    def init_template_installer(self, dist: Path, is_removed: bool) -> None:
        self._is_removed = is_removed
        self.build_state_widget.setExtract(False)
        self.build_dir = dist

        if self.build_info.branch == "bforartists":
            self.move_bforartists_patch_note()

        if get_install_template():
            self.progressBar.set_title("Copying data...")
            t = TemplateTask(destination=self.build_dir)
            t.finished.connect(self.download_get_info)
            self.parent.task_queue.append(t)
        else:
            self.download_get_info()

    def move_bforartists_patch_note(self) -> None:
        if self.build_dir is None:
            logger.error("Build directory is None, cannot move Bforartists patch note.")
            return

        bforartist_lib = self.build_dir.parent
        txt_files = [f for f in bforartist_lib.glob("*.txt") if f.is_file()]
        folders = [folder for folder in bforartist_lib.iterdir() if folder.is_dir()]

        for file in txt_files:
            file_version = ".".join(file.stem[-3:])
            for folder in folders:
                if file_version in folder.name:
                    try:
                        shutil.move(file, folder / file.name)
                    except shutil.Error as e:
                        logger.exception(f"Failed to move {file.name} to {folder.name}: {e}")

    def download_cancelled(self) -> None:
        self.item.setSelected(True)
        self.set_state(DownloadState.IDLE)
        self.cancelButton.hide()
        self.downloadButton.show()
        self.parent.task_queue.remove_task(self.dl_task)
        self.build_state_widget.setDownload(False)

    def download_get_info(self) -> None:
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

    def download_rename(self, build_info: BuildInfo) -> None:
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

    def download_finished(self, path: Path | None, is_removed: bool) -> None:
        if self._is_removed is False:
            self._is_removed = is_removed

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

            if widget:
                self.setInstalled(widget)

            if self.updating_widget is not None and self._is_removed is False:
                # Handle portable settings before removing old build
                if widget and self.updating_widget.move_portable_settings:
                    logger.debug("Transferring portable settings...")
                    QTimer.singleShot(500, lambda: self.handle_portable_settings(self.updating_widget, widget))
                else:
                    QTimer.singleShot(500, lambda: self.remove_old_build(self.updating_widget))

            if widget:
                widget.initialized.connect(lambda: self.parent.check_library_for_updates())

    def handle_portable_settings(self, old_widget: LibraryWidget, new_widget: LibraryWidget) -> None:
        """Handle portable settings transfer based on user choice."""

        if old_widget.move_portable_settings:
            old_config_path = old_widget.make_portable_path()

            if old_config_path.is_dir():
                # Wait for the new widget to be initialized
                if new_widget.build_info is None:
                    QTimer.singleShot(500, lambda: self.handle_portable_settings(old_widget, new_widget))
                    return

                new_config_path = new_widget.make_portable_path()

                try:
                    # Copy portable settings to new build
                    if new_config_path.parent.exists():
                        shutil.copytree(old_config_path, new_config_path, dirs_exist_ok=True)
                        logger.info(f"Portable settings moved from {old_config_path} to {new_config_path}")

                        # Update the new widget to reflect portable status once it's fully initialized
                        def update_portable_ui() -> None:
                            new_widget.makePortableAction.setText("Unmake Portable")
                            new_widget.showConfigFolderAction.setText("Show Portable Config Folder")

                        # Use the initialized signal to ensure UI elements are ready
                        new_widget.initialized.connect(update_portable_ui)
                    else:
                        logger.error(f"New config path parent does not exist: {new_config_path.parent}")
                        self._show_portable_failure_dialog(old_widget, "The new build directory can't be found.")
                        return
                except Exception as e:
                    logger.error(f"Failed to move portable settings: {e}")
                    self._show_portable_failure_dialog(old_widget, str(e))
                    return
            else:
                logger.warning(f"No portable settings found at {old_config_path} to move.")
                self._show_portable_failure_dialog(old_widget, "No portable settings found to transfer.")
                return

        self.remove_old_build(old_widget)

    def _show_portable_failure_dialog(self, old_widget: LibraryWidget, error: str) -> None:
        """Show dialog asking user how to handle portable settings transfer failure."""
        message = (
            f"Failed to transfer portable settings:\n{error}\n\nDo you want to continue with the update or cancel?"
        )

        popup = PopupWindow(
            message=message,
            title="Portable Settings Transfer Failed",
            icon=PopupIcon.WARNING,
            buttons=["Continue", "Cancel"],
            parent=self.parent,
        )

        popup.accepted.connect(lambda: self._handle_portable_failure_choice(old_widget, True))
        popup.cancelled.connect(lambda: self._handle_portable_failure_choice(old_widget))

    def _handle_portable_failure_choice(self, old_widget: LibraryWidget, continue_update: bool = False) -> None:
        """Handle the user's choice after portable settings transfer failure."""
        if continue_update:
            self.remove_old_build(old_widget)
        else:
            old_widget.update_finished()
            self.updating_widget = None

    def remove_old_build(self, widget: LibraryWidget) -> None:
        widget.confirm_major_version_update_removal(
            lambda should_remove: self._proceed_with_removal(widget, should_remove)
        )

    def _proceed_with_removal(self, widget: LibraryWidget, should_remove: bool) -> None:
        """Actually remove the old build based on user's choice."""
        if should_remove:
            widget.remove_from_drive(trash=True)

        widget.update_finished()
        self.updating_widget = None

    def setInstalled(self, build_widget: LibraryWidget) -> None:
        if self.state == DownloadState.IDLE:
            build_widget.destroyed.connect(self.uninstalled)
            self.downloadButton.hide()
            self.installedButton.show()
            self.cancelButton.hide()
            self.progressBar.hide()
            self.installed = build_widget

    @Slot()
    def uninstalled(self) -> None:
        self.installedButton.hide()
        self.downloadButton.show()
        self.installed = None

    @Slot(int, int, int)
    def _update_column_widths(self, version_width: int, _branch_width: int, commit_time_width: int) -> None:
        """Update column widths to match header splitter."""
        self.subversionLabel.setFixedWidth(version_width)
        self.commitTimeLabel.setFixedWidth(commit_time_width)
