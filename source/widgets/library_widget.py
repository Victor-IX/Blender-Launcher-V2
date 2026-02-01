from __future__ import annotations

import contextlib
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from i18n import t
from items.base_list_widget_item import BaseListWidgetItem
from modules.blender_update_manager import available_blender_update, is_major_version_update
from modules.build_info import (
    BuildInfo,
    LaunchMode,
    LaunchOpenLast,
    LaunchWithBlendFile,
    WriteBuildTask,
    get_fork_config_paths,
    launch_build,
)
from modules.enums import MessageType
from modules.platform_utils import _call, get_blender_config_folder, get_environment, get_platform, is_frozen
from modules.settings import (
    get_default_delete_action,
    get_favorite_path,
    get_library_folder,
    get_mark_as_favorite,
    get_show_update_button,
    set_favorite_path,
)
from modules.shortcut import generate_blender_shortcut, get_default_shortcut_destination
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QHoverEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget
from threads.observer import Observer
from threads.register import Register
from threads.remover import RemovalTask
from threads.template_installer import TemplateTask
from widgets.base_build_widget import BaseBuildWidget
from widgets.base_line_edit import BaseLineEdit
from widgets.base_menu_widget import BaseMenuWidget
from widgets.build_state_widget import BuildStateWidget
from widgets.datetime_widget import DateTimeWidget
from widgets.elided_text_label import ElidedTextLabel
from widgets.left_icon_button_widget import LeftIconButtonWidget
from windows.custom_build_dialog_window import CustomBuildDialogWindow
from windows.file_dialog_window import FileDialogWindow
from windows.popup_window import PopupIcon, PopupWindow

if TYPE_CHECKING:
    from widgets.base_list_widget import BaseListWidget
    from windows.main_window import BlenderLauncher

logger = logging.getLogger()


class LibraryWidget(BaseBuildWidget):
    def __init__(
        self,
        parent: BlenderLauncher,
        item: BaseListWidgetItem,
        link: Path,
        list_widget: BaseListWidget,
        build_info: BuildInfo,
        show_new=False,
        parent_widget=None,
    ):
        super().__init__(
            parent=parent,
            item=item,
            build_info=build_info,
        )
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self._hovering_and_shifting = False
        self._hovered = False

        self.parent: BlenderLauncher = parent
        self.link = Path(link)
        self.list_widget = list_widget
        self.show_new = show_new
        self.observer = None
        self.child_widget = None
        self.parent_widget = parent_widget
        self.move_portable_settings = False

        self.destroyed.connect(lambda: self._destroyed())

        self.outer_layout = QHBoxLayout()
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)

        # box should highlight when dragged over
        self.layout_widget = QWidget(self)
        self.layout: QHBoxLayout = QHBoxLayout()
        self.layout.setContentsMargins(2, 2, 0, 2)
        self.layout.setSpacing(0)
        self.layout_widget.setLayout(self.layout)
        self.outer_layout.addWidget(self.layout_widget)
        self.setLayout(self.outer_layout)

        self.branch = self.build_info.branch
        self.item.date = build_info.commit_time

        self.launchButton = LeftIconButtonWidget(t("act.launch"), parent=self)
        self.launchButton.setFixedWidth(95)
        self.launchButton.setProperty("LaunchButton", True)
        self._launch_icon = None

        self.updateButton = LeftIconButtonWidget("", self.parent.icons.update, parent=self)
        self.updateButton.setFixedWidth(25)
        self.updateButton.setProperty("UpdateButton", True)
        self.updateButton.setToolTip("Update Blender to the latest version")
        self.updateButton.hide()

        self.subversionLabel = QLabel(self.build_info.display_version)
        self.subversionLabel.setFixedWidth(85)
        self.subversionLabel.setIndent(20)
        self.subversionLabel.setToolTip(str(self.build_info.semversion))
        self.branchLabel = ElidedTextLabel(self.build_info.custom_name or self.build_info.display_label)
        self.commitTimeLabel = DateTimeWidget(self.build_info.commit_time, self.build_info.build_hash)

        self.build_state_widget = BuildStateWidget(self.parent.icons, self)

        self.layout.addWidget(self.launchButton)
        self.layout.addWidget(self.updateButton)
        self.layout.addWidget(self.subversionLabel)
        self.layout.addWidget(self.branchLabel, stretch=1)

        # Connect to column width changes from the page widget
        page_widget = self.list_widget.parent
        if page_widget is not None:
            page_widget.column_widths_changed.connect(self._update_column_widths)
            # Apply initial column widths
            widths = page_widget.get_column_widths()
            self._update_column_widths(widths[0], widths[1], widths[2])

        if self.parent_widget is not None:
            self.lineEdit = BaseLineEdit(self)
            self.lineEdit.setMaxLength(256)
            self.lineEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.lineEdit.escapePressed.connect(self.rename_branch_rejected)
            self.lineEdit.returnPressed.connect(self.rename_branch_accepted)
            self.layout.addWidget(self.lineEdit, stretch=1)
            self.lineEdit.hide()

        self.layout.addWidget(self.commitTimeLabel)
        self.layout.addWidget(self.build_state_widget)

        self.launchButton.clicked.connect(
            lambda: self.launch(
                update_selection=True,
                launch_mode=LaunchOpenLast() if self.hovering_and_shifting else None,
            )
        )
        self.launchButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.updateButton.setCursor(Qt.CursorShape.PointingHandCursor)

        # Context menu
        self.menu_extended = BaseMenuWidget(parent=self)
        self.menu_extended.setFont(self.parent.font_10)

        # For checking if shift is held on menus
        self.menu.enable_shifting()
        self.menu_extended.enable_shifting()
        self.menu.holding_shift.connect(self.update_delete_action)
        self.menu.holding_shift.connect(self.update_config_action)
        self.menu_extended.holding_shift.connect(self.update_delete_action)

        self.deleteAction = QAction(t("act.a.delete"), self)
        self.deleteAction.setIcon(self.parent.icons.delete)
        self.deleteAction.triggered.connect(self.ask_remove_from_drive)

        self.editAction = QAction(t("act.a.edit"), self)
        self.editAction.setIcon(self.parent.icons.settings)
        self.editAction.triggered.connect(self.edit_build)

        self.openRecentAction = QAction(t("act.a.prev"), self)
        self.openRecentAction.setIcon(self.parent.icons.file)
        self.openRecentAction.triggered.connect(lambda: self.launch(launch_mode=LaunchOpenLast()))
        self.openRecentAction.setToolTip(t("act.a.prev_tooltip"))

        self.addToQuickLaunchAction = QAction(t("act.a.quick_launch"), self)
        self.addToQuickLaunchAction.setIcon(self.parent.icons.quick_launch)
        self.addToQuickLaunchAction.triggered.connect(self.add_to_quick_launch)

        self.addToFavoritesAction = QAction(t("act.a.fav.add"), self)
        self.addToFavoritesAction.setIcon(self.parent.icons.favorite)
        self.addToFavoritesAction.triggered.connect(self.add_to_favorites)

        self.removeFromFavoritesAction = QAction(t("act.fav.rem"), self)
        self.removeFromFavoritesAction.setIcon(self.parent.icons.favorite)
        self.removeFromFavoritesAction.triggered.connect(self.remove_from_favorites)

        if self.parent_widget is not None:
            self.addToFavoritesAction.setVisible(False)
        else:
            self.removeFromFavoritesAction.setVisible(False)

        self.updateBlenderBuildAction = QAction(t("act.a.update"))
        self.updateBlenderBuildAction.setIcon(self.parent.icons.update)
        self.updateBlenderBuildAction.triggered.connect(self.trigger_update_download)
        self.updateBlenderBuildAction.setToolTip(t("act.a.update_tooltip"))
        self.updateBlenderBuildAction.setVisible(False)

        self.registerExtentionAction = QAction(t("act.a.register"))
        self.registerExtentionAction.setToolTip(t("act.a.register_tooltip"))
        self.registerExtentionAction.triggered.connect(self.register_extension)

        self.createShortcutAction = QAction(t("act.a.shortcut"))
        self.createShortcutAction.triggered.connect(self.create_shortcut)

        self.showBuildFolderAction = QAction(t("act.a.folder_build"))
        self.showBuildFolderAction.setIcon(self.parent.icons.folder)
        self.showBuildFolderAction.triggered.connect(self.show_build_folder)

        config_path = self.make_portable_path()

        self.showConfigFolderAction = QAction(t("act.a.config_portable") if config_path.is_dir() else t("act.a.config"))
        self.showConfigFolderAction.setIcon(self.parent.icons.folder)
        self.showConfigFolderAction.triggered.connect(self.show_config_folder)

        self.createSymlinkAction = QAction(t("act.a.symlink"))
        self.createSymlinkAction.triggered.connect(self.create_symlink)

        self.installTemplateAction = QAction(t("act.a.template"))
        self.installTemplateAction.triggered.connect(self.install_template)

        self.makePortableAction = QAction(t("act.a.port.rem") if config_path.is_dir() else t("act.a.port.add"))
        self.makePortableAction.triggered.connect(self.make_portable)

        self.copyBuildHash = QAction(t("act.a.hash"))
        self.copyBuildHash.triggered.connect(self.copy_build_hash)

        self.freezeUpdate = QAction(t("act.a.freeze.rem") if self.build_info.is_frozen else t("act.a.freeze.add"))
        self.freezeUpdate.triggered.connect(self.freeze_update)

        self.debugMenu = BaseMenuWidget(t("act.a.d.d"), parent=self)
        self.debugMenu.setFont(self.parent.font_10)

        self.debugLogAction = QAction(t("act.a.d.log"))
        self.debugLogAction.triggered.connect(lambda: self.launch(exe="blender_debug_log.cmd"))
        self.debugFactoryStartupAction = QAction(t("act.a.d.factory"))
        self.debugFactoryStartupAction.triggered.connect(lambda: self.launch(exe="blender_factory_startup.cmd"))
        self.debugGpuTemplateAction = QAction(t("act.a.d.gpu"))
        self.debugGpuTemplateAction.triggered.connect(lambda: self.launch(exe="blender_debug_gpu.cmd"))
        self.debugGpuGWTemplateAction = QAction(t("act.a.d.glitch"))
        self.debugGpuGWTemplateAction.triggered.connect(
            lambda: self.launch(exe="blender_debug_gpu_glitchworkaround.cmd")
        )

        self.debugMenu.addAction(self.debugLogAction)
        self.debugMenu.addAction(self.debugFactoryStartupAction)
        self.debugMenu.addAction(self.debugGpuTemplateAction)
        self.debugMenu.addAction(self.debugGpuGWTemplateAction)

        self.menu.addAction(self.openRecentAction)
        self.menu.addAction(self.addToQuickLaunchAction)
        self.menu.addAction(self.addToFavoritesAction)
        self.menu.addAction(self.removeFromFavoritesAction)
        self.menu.addAction(self.updateBlenderBuildAction)
        self.menu.addMenu(self.debugMenu)

        if self.parent_widget is not None:
            self.renameBranchAction = QAction(t("act.a.rename"))
            self.renameBranchAction.triggered.connect(self.rename_branch)
            self.menu.addAction(self.renameBranchAction)

        self.menu.addSeparator()

        if get_platform() == "Windows":
            self.menu.addAction(self.registerExtentionAction)

        self.menu.addAction(self.createShortcutAction)
        self.menu.addAction(self.createSymlinkAction)
        self.menu.addAction(self.installTemplateAction)
        self.menu.addAction(self.makePortableAction)
        self.menu.addAction(self.copyBuildHash)
        self.menu.addAction(self.freezeUpdate)
        self.menu.addSeparator()

        if self.branch in {"stable", "lts", "bforartists", "daily"}:
            self.menu.addAction(self.showReleaseNotesAction)
        else:
            exp = re.compile(r"D\d{5}")
            if exp.search(self.build_info.branch):
                self.showReleaseNotesAction.setText(t("act.a.release_notes_patch"))
                self.menu.addAction(self.showReleaseNotesAction)
            else:
                exp = re.compile(r"pr\d+", flags=re.IGNORECASE)
                if exp.search(self.build_info.branch):
                    self.showReleaseNotesAction.setText(t("act.a.release_notes_pr"))
                    self.menu.addAction(self.showReleaseNotesAction)

        self.menu.addAction(self.showBuildFolderAction)
        self.menu.addAction(self.showConfigFolderAction)
        self.menu.addAction(self.editAction)
        self.menu.addAction(self.deleteAction)

        self.menu_extended.addAction(self.deleteAction)

        if self.show_new:
            self.build_state_widget.setNewBuild(True)

            if get_mark_as_favorite() == 0:
                pass
            elif get_mark_as_favorite() == 1 and self.branch == "stable":
                self.add_to_quick_launch()
            elif get_mark_as_favorite() == 2 and self.branch == "daily":
                self.add_to_quick_launch()
            elif get_mark_as_favorite() == 3:
                self.add_to_quick_launch()
        elif get_favorite_path() == self.link.as_posix():
            self.add_to_quick_launch()

        self.setEnabled(True)
        self.list_widget.sortItems()

        if self.build_info.is_favorite and self.parent_widget is None:
            self.add_to_favorites()

    def context_menu(self):
        self.update_delete_action(self.hovering_and_shifting)
        self.update_config_action(self.hovering_and_shifting)

        if len(self.list_widget.selectedItems()) > 1:
            self.menu_extended.trigger()
            return

        self.createSymlinkAction.setEnabled(True)
        link_path = Path(get_library_folder()) / "bl_symlink"

        if link_path.exists() and (link_path.is_dir() or link_path.is_symlink()) and link_path.resolve() == self.link:
            self.createSymlinkAction.setEnabled(False)

        self.menu.trigger()

    @Slot(bool)
    def update_delete_action(self, shifting: bool):
        reverted_behavior = get_default_delete_action() == 1
        delete_from_drive = not reverted_behavior if shifting else reverted_behavior

        if delete_from_drive:
            self.deleteAction.setText(t("act.a.delete"))
        else:
            self.deleteAction.setText(t("act.a.trash"))

    @Slot(bool)
    def update_config_action(self, shifting: bool):
        config_path = self.make_portable_path()

        if config_path.is_dir() and not shifting:
            self.showConfigFolderAction.setText(t("act.a.config_portable"))
        else:
            self.showConfigFolderAction.setText(t("act.a.config"))

    def mouseDoubleClickEvent(self, _event):
        if self.hovering_and_shifting:
            self.launch(launch_mode=LaunchOpenLast())

    def mouseReleaseEvent(self, event):
        if event.button == Qt.MouseButton.LeftButton:
            if self.show_new is True:
                self.build_state_widget.setNewBuild(False)
                self.show_new = False

            mod = QApplication.keyboardModifiers()
            if mod not in (
                Qt.KeyboardModifier.ShiftModifier,
                Qt.KeyboardModifier.ControlModifier,
            ):
                self.list_widget.clearSelection()
                self.item.setSelected(True)

            event.accept()

        event.ignore()

    def dragEnterEvent(self, e: QDragEnterEvent):
        mime_data = e.mimeData()
        if (
            mime_data is not None
            and mime_data.hasUrls()
            and mime_data.hasFormat("text/uri-list")
            and all(
                url.isLocalFile()
                and Path(url.fileName()).suffix in (".blend", ".blend1", ".blend2", ".blend3", ".blend4")
                for url in mime_data.urls()
            )
        ):
            self.setStyleSheet("background-color: #4EA13A")
            e.accept()
        else:
            e.ignore()

    def dragLeaveEvent(self, _e: QDragLeaveEvent):
        self.setStyleSheet("background-color:")

    def dropEvent(self, e: QDropEvent):
        mime_data = e.mimeData()
        assert mime_data is not None
        for file in mime_data.urls():
            self.launch(True, launch_mode=LaunchWithBlendFile(Path(file.toLocalFile())))
        self.setStyleSheet("background-color:")

    def eventFilter(self, obj, event):
        # For detecting SHIFT
        if isinstance(event, QHoverEvent):
            if self._hovered and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.hovering_and_shifting = True
            else:
                self.hovering_and_shifting = False
        return super().eventFilter(obj, event)

    def _shift_hovering(self):
        self.launchButton.set_text(t("act.lprev"))
        self._launch_icon = self.launchButton.icon()
        self.launchButton.setIcon(self.parent.icons.file)
        self.launchButton.setFont(self.parent.font_8)

    def _stopped_shift_hovering(self):
        self.launchButton.set_text(t("act.launch"))
        self.launchButton.setIcon(self._launch_icon or self.parent.icons.none)
        self.launchButton.setFont(self.parent.font_10)

    def enterEvent(self, _e):
        self._hovered = True

    def leaveEvent(self, _e):
        self._hovered = False

    @property
    def hovering_and_shifting(self):
        return self._hovering_and_shifting

    @hovering_and_shifting.setter
    def hovering_and_shifting(self, v: bool):
        if v and not self._hovering_and_shifting:
            self._hovering_and_shifting = True
            self._shift_hovering()
        elif not v and self._hovering_and_shifting:
            self._hovering_and_shifting = False
            self._stopped_shift_hovering()

    def install_template(self):
        self.launchButton.set_text(t("act.updating"))
        self.launchButton.setEnabled(False)
        self.deleteAction.setEnabled(False)
        self.installTemplateAction.setEnabled(False)
        a = TemplateTask(self.link)
        a.finished.connect(self.install_template_finished)
        self.parent.task_queue.append(a)

    def install_template_finished(self):
        self.launchButton.set_text(t("act.launch"))
        self.launchButton.setEnabled(True)
        self.deleteAction.setEnabled(True)
        self.installTemplateAction.setEnabled(True)

    def launch(self, update_selection=False, exe=None, launch_mode: LaunchMode | None = None):
        if update_selection is True:
            self.list_widget.clearSelection()
            self.item.setSelected(True)

        if self.parent_widget is not None:
            self.parent_widget.launch()
            return

        if self.show_new is True:
            self.build_state_widget.setNewBuild(False)
            self.show_new = False

        proc = launch_build(self.build_info, exe, launch_mode=launch_mode)

        assert proc is not None
        if self.observer is None:
            self.observer = Observer(self)
            self.observer.count_changed.connect(self.proc_count_changed)
            self.observer.started.connect(self.observer_started)
            self.observer.finished.connect(self.observer_finished)
            self.observer.start()

        self.observer.append_proc.emit(proc)

    def update_finished(self):
        """Reset the widget state after update completion."""
        self.launchButton.set_text(t("act.launch"))
        self.launchButton.setEnabled(True)
        if hasattr(self, "_update_download_widget"):
            delattr(self, "_update_download_widget")
        logger.debug(f"Update finished for {self.link.name}")

    def show_update_button(self):
        """Show update button and adjust layout."""
        self.updateButton.show()
        self.launchButton.setFixedWidth(70)

    def _hide_update_button(self):
        """Hide update button and reset layout."""
        self.updateButton.hide()
        self.launchButton.setFixedWidth(95)
        self.updateBlenderBuildAction.setVisible(False)

    def check_for_updates(self, available_downloads):
        logger.debug(
            f"Checking for updates for {self.build_info.semversion.replace(prerelease=None)} in {self.build_info.branch} branch."
        )

        # Skip update check if build is frozen
        if self.build_info.is_frozen:
            self._hide_update_button()
            return False

        update = available_blender_update(self.build_info, available_downloads, self.list_widget.items())
        if update:
            if get_show_update_button():
                self.show_update_button()
                self.updateBlenderBuildAction.setVisible(True)
            else:
                self._hide_update_button()

            self._update_download_widget = update

            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self.updateButton.clicked.disconnect()
            self.updateButton.clicked.connect(self.trigger_update_download)
            return True

        self._hide_update_button()
        return False

    def trigger_update_download(self):
        if hasattr(self, "_update_download_widget"):
            self._is_major_version_update = is_major_version_update(self.build_info, self._update_download_widget)
        else:
            self._is_major_version_update = False

        config_path = self.make_portable_path()
        if config_path.is_dir():
            self._show_portable_settings_dialog()
        else:
            self._proceed_with_update()

    def _show_portable_settings_dialog(self):
        """Show dialog asking what to do with portable settings."""
        message = "This build uses portable settings.\n\nWhat would you like to do with the portable settings folder?"

        self._portable_popup = PopupWindow(
            message=message,
            title="Portable Settings",
            icon=PopupIcon.WARNING,
            buttons=["Move to New Version", "Remove Settings", "Cancel"],
            parent=self.parent,
        )

        self._portable_popup.custom_signal.connect(self._handle_portable_choice)

    def _handle_portable_choice(self, choice: str):
        """Handle the user's choice for portable settings."""
        if choice == "Move to New Version":
            self.move_portable_settings = True
            self._proceed_with_update()
        elif choice == "Remove Settings":
            self._proceed_with_update()
        else:  # Cancel
            # Reset the UI state
            self.launchButton.set_text(t("act.launch"))
            self.launchButton.setEnabled(True)
            if hasattr(self, "_update_download_widget") and get_show_update_button():
                self.show_update_button()

    def _proceed_with_update(self):
        """Proceed with the actual update download."""
        self._hide_update_button()
        self.launchButton.set_text(t("act.updating"))
        self.launchButton.setEnabled(False)

        if hasattr(self, "_update_download_widget"):
            self._update_download_widget.init_downloader(updating_widget=self)
            # Safely disconnect any existing connections
            # Suppress RuntimeWarning for disconnecting when no connections exist
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self.updateButton.clicked.disconnect()

    def confirm_major_version_update_removal(self, callback):
        """Show confirmation dialog for major version update before removing old build."""
        if hasattr(self, "_update_download_widget"):
            update_download_widget = self._update_download_widget

        if update_download_widget and is_major_version_update(self.build_info, update_download_widget):
            current_version = self.build_info.semversion.replace(prerelease=None)
            update_version = update_download_widget.build_info.semversion.replace(prerelease=None)

            message = (
                f"Updating from {current_version} to {update_version} will use a new set of Blender Preferences\n\n"
                f"Do you want to remove the old build ({current_version}) from your library?"
            )

            self._confirmation_popup = PopupWindow(
                message=message,
                title="Major Version Update - Remove Old Build",
                icon=PopupIcon.WARNING,
                buttons=["Remove", "Keep Both Versions"],
                parent=self.parent,
            )

            self._confirmation_popup.accepted.connect(lambda: self._handle_removal_confirmation(callback, True))
            self._confirmation_popup.cancelled.connect(lambda: self._handle_removal_confirmation(callback, False))
        else:
            callback(True)

    def _handle_removal_confirmation(self, callback, remove_old_build):
        callback(remove_old_build)

    def proc_count_changed(self, count):
        self.build_state_widget.setCount(count)

        if self.child_widget is not None:
            self.child_widget.proc_count_changed(count)

    def observer_started(self):
        self.deleteAction.setEnabled(False)
        self.installTemplateAction.setEnabled(False)

        if self.child_widget is not None:
            self.child_widget.observer_started()

    def observer_finished(self):
        self.observer = None
        self.build_state_widget.setCount(0)
        self.deleteAction.setEnabled(True)
        self.installTemplateAction.setEnabled(True)

        if self.child_widget is not None:
            self.child_widget.observer_finished()

    @Slot()
    def make_portable(self):
        config_path = self.make_portable_path()
        folder_name = config_path.name
        _config_path = config_path.parent / ("_" + folder_name)

        if config_path.is_dir():
            config_path.rename(_config_path)
            self.makePortableAction.setText(t("act.a.port.add"))
            self.showConfigFolderAction.setText(t("act.a.config"))
        else:
            if _config_path.is_dir():
                _config_path.rename(config_path)
            else:
                config_path.mkdir(parents=False, exist_ok=True)
            self.makePortableAction.setText(t("act.a.port.rem"))
            self.showConfigFolderAction.setText(t("act.a.config_portable"))

    def make_portable_path(self) -> Path:
        version = self.build_info.subversion.rsplit(".", 1)[0]
        branch = self.build_info.branch

        if branch == "bforartists" and version >= "4.1":
            folder_name = "portable"
            config_path = self.link / folder_name
        elif "upbge" in branch and version >= "0.42":
            folder_name = "portable"
            config_path = self.link / folder_name
        elif version >= "4.2":
            folder_name = "portable"
            config_path = self.link / folder_name
        else:
            folder_name = "config"
            config_path = self.link / version / folder_name

        return config_path

    @Slot()
    def copy_build_hash(self):
        if self.build_info is None:
            error_msg = "Unable to copy build hash: build information not available."
            logger.error(error_msg)
            self.parent.show_message(error_msg, message_type=MessageType.ERROR)
            return

        if self.build_info.build_hash is None:
            error_msg = "Unable to copy build hash: hash not available for this build."
            logger.error(error_msg)
            self.parent.show_message(error_msg, message_type=MessageType.ERROR)
            return

        QApplication.clipboard().setText(self.build_info.build_hash)

    @Slot()
    def freeze_update(self):
        if self.build_info is None:
            error_msg = "Unable to freeze/unfreeze update: build information not available."
            logger.error(error_msg)
            self.parent.show_message(error_msg, message_type=MessageType.ERROR)
            return

        if self.build_info.is_frozen:
            self.build_info.is_frozen = False
            self.freezeUpdate.setText(t("act.a.freeze.add"))
        else:
            self.build_info.is_frozen = True
            self.freezeUpdate.setText(t("act.a.freeze.rem"))
            self._hide_update_button()

        self.write_build_info()

    @Slot()
    def rename_branch(self):
        self.lineEdit.setText(self.branchLabel.text)
        self.lineEdit.selectAll()
        self.lineEdit.setFocus()
        self.lineEdit.show()
        self.branchLabel.hide()

    @Slot()
    def rename_branch_accepted(self):
        self.lineEdit.hide()
        name = self.lineEdit.text().strip()

        if name:
            self.branchLabel.set_text(name)
            self.build_info.custom_name = name
            self.write_build_info()
        else:
            error_msg = "Branch name cannot be empty."
            logger.error(error_msg)
            self.parent.show_message(error_msg, message_type=MessageType.ERROR)

        self.branchLabel.show()

    @Slot()
    def rename_branch_rejected(self):
        self.lineEdit.hide()
        self.branchLabel.show()

    def write_build_info(self):
        self.build_info_writer = WriteBuildTask(
            self.link,
            self.build_info,
        )
        self.build_info_writer.written.connect(self.build_info_writer_finished)
        self.parent.task_queue.append(self.build_info_writer)

    def build_info_writer_finished(self):
        self.build_info_writer = None

    @Slot()
    def ask_remove_from_drive(self):
        reverted_behavior = get_default_delete_action() == 1
        mod = QApplication.keyboardModifiers()
        is_shift_pressed = mod == Qt.KeyboardModifier.ShiftModifier

        # if not shift clicked (or reversed action), ask to send to trash instead of deleting
        if (not is_shift_pressed and not reverted_behavior) or (is_shift_pressed and reverted_behavior):
            self.ask_send_to_trash()
            return

        self.item.setSelected(True)
        self.dlg = PopupWindow(
            parent=self.parent,
            title="Warning",
            message="Are you sure you want to<br>delete selected builds?",
            icon=PopupIcon.NONE,
            buttons=["Yes", "No"],
        )

        if len(self.list_widget.selectedItems()) > 1:
            self.dlg.accepted.connect(self.remove_from_drive_extended)
        else:
            self.dlg.accepted.connect(self.remove_from_drive)

    @Slot()
    def remove_from_drive_extended(self):
        for item in self.list_widget.selectedItems():
            widget = self.list_widget.itemWidget(item)
            if widget is not None and isinstance(widget, LibraryWidget):
                widget.remove_from_drive()

    @Slot()
    def remove_from_drive(self, trash=False):
        if self.parent_widget is not None:
            self.parent_widget.remove_from_drive()
            return

        path = get_library_folder() / self.link
        a = RemovalTask(path, trash=trash)
        a.finished.connect(self.remover_completed)
        self.parent.task_queue.append(a)
        self.remover_started()

    @Slot()
    def ask_send_to_trash(self):
        self.item.setSelected(True)
        self.dlg = PopupWindow(
            parent=self.parent,
            title="Warning",
            message="Are you sure you want to<br> \
                  send selected builds to trash?",
            icon=PopupIcon.NONE,
            buttons=["Yes", "No"],
        )

        if len(self.list_widget.selectedItems()) > 1:
            self.dlg.accepted.connect(self.send_to_trash_extended)
        else:
            self.dlg.accepted.connect(self.send_to_trash)

    @Slot()
    def send_to_trash_extended(self):
        for item in self.list_widget.selectedItems():
            widget = self.list_widget.itemWidget(item)
            if widget is not None and isinstance(widget, LibraryWidget):
                widget.remove_from_drive(trash=True)

    @Slot()
    def send_to_trash(self):
        self.remove_from_drive(trash=True)

    # TODO Clear icon if build in quick launch
    def remover_started(self):
        self.launchButton.set_text(t("act.deleting"))
        self.setEnabled(False)
        self.item.setFlags(self.item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        if self.child_widget is not None:
            self.child_widget.remover_started()

    def remover_completed(self, code):
        if self.child_widget is not None:
            self.child_widget.remover_completed(code)

        if code == 0:
            self.list_widget.remove_item(self.item)

            if self.parent_widget is None:
                self.parent.draw_from_cashed(self.build_info)

            return
        # TODO Child synchronization and reverting selection flags
        self.launchButton.set_text("Launch")
        self.setEnabled(True)
        return

    @Slot()
    def edit_build(self):
        dlg = CustomBuildDialogWindow(self.parent, Path(self.build_info.link), self.build_info)
        dlg.accepted.connect(self.build_info_edited)

    @Slot(BuildInfo)
    def build_info_edited(self, blinfo: BuildInfo):
        self.list_widget.remove_item(self.item)
        blinfo.write_to(Path(blinfo.link))
        self.parent.draw_to_library(Path(blinfo.link), show_new=True)

    @Slot()
    def add_to_quick_launch(self):
        if (self.parent.favorite is not None) and (self.parent.favorite.link != self.link):
            self.parent.favorite.remove_from_quick_launch()

        set_favorite_path(self.link.as_posix())
        self.parent.favorite = self

        self.launchButton.setIcon(self.parent.icons.quick_launch)
        self.addToQuickLaunchAction.setEnabled(False)

        # TODO Make more optimal and simpler synchronization
        if self.parent_widget is not None:
            self.parent_widget.launchButton.setIcon(self.parent.icons.quick_launch)
            self.parent_widget.addToQuickLaunchAction.setEnabled(False)

        if self.child_widget is not None:
            self.child_widget.launchButton.setIcon(self.parent.icons.quick_launch)
            self.child_widget.addToQuickLaunchAction.setEnabled(False)

    @Slot()
    def remove_from_quick_launch(self):
        self.launchButton.setIcon(self.parent.icons.fake)
        self.addToQuickLaunchAction.setEnabled(True)

        # TODO Make more optimal and simpler synchronization
        if self.parent_widget is not None:
            self.parent_widget.launchButton.setIcon(self.parent.icons.fake)
            self.parent_widget.addToQuickLaunchAction.setEnabled(True)

        if self.child_widget is not None:
            self.child_widget.launchButton.setIcon(self.parent.icons.fake)
            self.child_widget.addToQuickLaunchAction.setEnabled(True)

    @Slot()
    def add_to_favorites(self):
        item = BaseListWidgetItem()
        widget = LibraryWidget(
            self.parent,
            item,
            self.link,
            self.parent.FavoritesPage.list_widget,
            build_info=self.build_info,
            parent_widget=self,
        )
        if not self.parent.FavoritesPage.list_widget.contains_build_info(self.build_info):
            self.parent.FavoritesPage.list_widget.insert_item(item, widget)
        self.child_widget = widget

        self.removeFromFavoritesAction.setVisible(True)
        self.addToFavoritesAction.setVisible(False)
        if self.build_info.is_favorite is False:
            self.build_info.is_favorite = True
            self.write_build_info()

    @Slot()
    def remove_from_favorites(self):
        widget = self.parent_widget or self
        assert widget.child_widget is not None
        self.parent.FavoritesPage.list_widget.remove_item(widget.child_widget.item)

        widget.child_widget = None
        widget.removeFromFavoritesAction.setVisible(False)
        widget.addToFavoritesAction.setVisible(True)

        self.build_info.is_favorite = False
        self.build_info_writer = WriteBuildTask(self.link, self.build_info)
        self.parent.task_queue.append(self.build_info_writer)

    @Slot()
    def register_extension(self):
        path = Path(get_library_folder()) / self.link
        self.register = Register(path)
        self.register.start()

    @Slot()
    def create_shortcut(self):
        name = "Blender {} {}".format(
            self.build_info.subversion.replace("(", "").replace(")", ""),
            self.build_info.branch.replace("-", " ").title(),
        )

        destination = get_default_shortcut_destination(name)
        file_place = FileDialogWindow().get_save_filename(
            parent=self, title="Choose destination", directory=str(destination)
        )
        if file_place[0]:
            generate_blender_shortcut(self.link, name, Path(file_place[0]))

    @Slot()
    def create_symlink(self):
        target = self.link.as_posix()
        link_path = Path(get_library_folder()) / "bl_symlink"
        link = link_path.as_posix()
        platform = get_platform()

        if platform == "Windows":
            with contextlib.suppress(Exception):
                link_path.rmdir()

            _call(f'mklink /J "{link}" "{target}"')
        elif platform == "Linux":
            if link_path.exists() and link_path.is_symlink():
                link_path.unlink()

            link_path.symlink_to(target)

    @Slot()
    def show_folder(self, folder_path: Path):
        if not folder_path:
            logger.debug("Path is empty or not specified.")
            return

        if not folder_path.is_dir():
            logger.error(f"Path {folder_path} do not exist.")
            return

        if QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path.as_posix())):
            return

        platform = get_platform()

        if platform == "Windows":
            os.startfile(folder_path.as_posix())
        elif platform == "macOS":
            subprocess.call(["open", folder_path.as_posix()])
        elif platform == "Linux":
            # Due to a bug/feature in Pyinstaller, we
            # have to remove all environment variables
            # that reference tmp in order for xdg-open
            # to work.
            env_override = get_environment()

            # Check if the program was built with Pyinstaller
            if is_frozen():
                toDelete = []
                for k, v in env_override.items():
                    if k != "PATH" and "tmp" in v:
                        toDelete.append(k)

                for k in toDelete:
                    env_override.pop(k, None)

            # Use specific file managers known to be common in Linux
            try:
                subprocess.call(["xdg-open", folder_path.as_posix()], env=env_override)
            except FileNotFoundError:
                # Try known file managers if xdg-open fails
                for fm in ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo"]:
                    if subprocess.call([fm, folder_path.as_posix()], env=env_override) == 0:
                        return
                logger.error("No file manager found to open the folder.")

    @Slot()
    def show_build_folder(self):
        library_folder = Path(get_library_folder())
        path = library_folder / self.link
        self.show_folder(path)

    @Slot()
    def show_config_folder(self):
        mod = QApplication.keyboardModifiers()
        is_shift_pressed = mod == Qt.KeyboardModifier.ShiftModifier
        config_path = self.make_portable_path()

        if config_path.is_dir() and not is_shift_pressed:
            self.show_folder(config_path)
            return

        version = self.build_info.semversion
        branch = self.build_info.branch
        custom_folder = None
        custom_subfolder = None

        fork_config = get_fork_config_paths(branch)
        if fork_config is not None:
            custom_folder = fork_config["config_folder"]
            subfolder_config = fork_config["config_subfolder"]

            # Handle platform-specific subfolder
            if isinstance(subfolder_config, dict):
                platform = get_platform()
                custom_subfolder = subfolder_config.get(platform)
            else:
                custom_subfolder = subfolder_config

            # Get version from version matcher
            if branch == "bforartists":
                version = self.build_info.bforartist_version_matcher
            elif branch.startswith("upbge"):
                version = self.build_info.upbge_version_matcher

        if version is None:
            version_str = ""
        else:
            version_str = f"{version.major}.{version.minor}"

        kwargs = {
            k: v
            for k, v in {
                "config_folder_name": custom_folder,
                "config_subfolder_name": custom_subfolder,
            }.items()
            if v is not None
        }

        base_config_path = get_blender_config_folder(**kwargs)

        if base_config_path is None:
            logger.error("Unable to determine base configuration path.")
            PopupWindow(
                title="Error",
                message="Unable to determine configuration folder path.",
                info_popup=True,
                icon=PopupIcon.WARNING,
                parent=self.parent,
            )
            return

        path = base_config_path / version_str
        general_path = base_config_path

        if not path.is_dir():
            logger.warning(f"Config folder {path} do not exist.")
            popup = PopupWindow(
                title="Warning",
                message="No config folder found for this version.",
                buttons=["Open General Config Folder", "Cancel"],
                icon=PopupIcon.WARNING,
                parent=self.parent,
            )
            popup.accepted.connect(lambda: self.show_folder(general_path))
            popup.show()
            return

        self.show_folder(path)

    def _destroyed(self):
        if self.parent.favorite == self:
            self.parent.favorite = None

    @Slot(int, int, int)
    def _update_column_widths(self, version_width: int, _branch_width: int, commit_time_width: int):
        """Update column widths to match header splitter."""
        if not hasattr(self, "subversionLabel") or self.subversionLabel is None:
            return
        self.subversionLabel.setFixedWidth(version_width)
        self.commitTimeLabel.setFixedWidth(commit_time_width)
