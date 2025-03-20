from __future__ import annotations

import contextlib
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from items.base_list_widget_item import BaseListWidgetItem
from modules._platform import _call, get_blender_config_folder, get_platform, is_frozen, get_environment
from modules.build_info import (
    BuildInfo,
    LaunchMode,
    LaunchOpenLast,
    LaunchWithBlendFile,
    ReadBuildTask,
    WriteBuildTask,
    launch_build,
)
from modules.settings import (
    get_default_delete_action,
    get_favorite_path,
    get_library_folder,
    get_mark_as_favorite,
    set_favorite_path,
)
from modules.shortcut import generate_blender_shortcut, get_default_shortcut_destination
from PySide6 import QtCore
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QHoverEvent,
)
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
from windows.popup_window import PopupIcon, PopupWindow
from windows.file_dialog_window import FileDialogWindow

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher

logger = logging.getLogger()


class LibraryWidget(BaseBuildWidget):
    initialized = Signal()

    def __init__(
        self,
        parent: BlenderLauncher,
        item: BaseListWidgetItem,
        link,
        list_widget,
        show_new=False,
        parent_widget=None,
    ):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self._hovering_and_shifting = False
        self._hovered = False

        self.parent: BlenderLauncher = parent
        self.item: BaseListWidgetItem = item
        self.link = link
        self.list_widget = list_widget
        self.show_new = show_new
        self.observer = None
        self.build_info: BuildInfo | None = None
        self.child_widget = None
        self.parent_widget = parent_widget
        self.is_damaged = False

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

        if self.parent_widget is None:
            self.setEnabled(False)
            self.infoLabel = QLabel("Loading build information...")
            self.infoLabel.setWordWrap(True)

            self.launchButton = LeftIconButtonWidget("", parent=self)
            self.launchButton.setFixedWidth(85)
            self.launchButton.setProperty("CancelButton", True)

            self.layout.addWidget(self.launchButton)
            self.layout.addWidget(self.infoLabel, stretch=1)

            a = ReadBuildTask(link)
            a.finished.connect(self.draw)
            a.failure.connect(self.trigger_damaged)

            self.parent.task_queue.append(a)

        else:
            self.draw(self.parent_widget.build_info)

    @Slot()
    def trigger_damaged(self):
        self.infoLabel.setText(f"Build *{Path(self.link).name}* is damaged!")
        self.launchButton.set_text("Delete")
        self.launchButton.clicked.connect(self.ask_remove_from_drive)
        self.setEnabled(True)
        self.is_damaged = True

    def draw(self, build_info: BuildInfo):
        if self.parent_widget is None:
            for i in reversed(range(self.layout.count())):
                self.layout.itemAt(i).widget().setParent(None)

        self.build_info = build_info
        self.branch = self.build_info.branch
        self.item.date = build_info.commit_time

        self.launchButton = LeftIconButtonWidget("Launch", parent=self)
        self.launchButton.setFixedWidth(85)
        self.launchButton.setProperty("LaunchButton", True)
        self._launch_icon = None

        self.subversionLabel = QLabel(self.build_info.display_version)
        self.subversionLabel.setFixedWidth(85)
        self.subversionLabel.setIndent(20)
        self.subversionLabel.setToolTip(str(self.build_info.semversion))
        self.branchLabel = ElidedTextLabel(self.build_info.custom_name or self.build_info.display_label)
        self.commitTimeLabel = DateTimeWidget(self.build_info.commit_time, self.build_info.build_hash)

        self.build_state_widget = BuildStateWidget(self.parent.icons, self)

        self.layout.addWidget(self.launchButton)
        self.layout.addWidget(self.subversionLabel)
        self.layout.addWidget(self.branchLabel, stretch=1)

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

        # Context menu
        self.menu_extended = BaseMenuWidget(parent=self)
        self.menu_extended.setFont(self.parent.font_10)

        # For checking if shift is held on menus
        self.menu.enable_shifting()
        self.menu_extended.enable_shifting()
        self.menu.holding_shift.connect(self.update_delete_action)
        self.menu.holding_shift.connect(self.update_config_action)
        self.menu_extended.holding_shift.connect(self.update_delete_action)

        self.deleteAction = QAction("Delete From Drive", self)
        self.deleteAction.setIcon(self.parent.icons.delete)
        self.deleteAction.triggered.connect(self.ask_remove_from_drive)

        self.editAction = QAction("Edit Build...", self)
        self.editAction.setIcon(self.parent.icons.settings)
        self.editAction.triggered.connect(self.edit_build)

        self.openRecentAction = QAction("Open Previous File", self)
        self.openRecentAction.setIcon(self.parent.icons.file)
        self.openRecentAction.triggered.connect(lambda: self.launch(launch_mode=LaunchOpenLast()))
        self.openRecentAction.setToolTip(
            "This action opens the last file used in this build."
            "\n(Appends `--open-last` to the execution arguments)"
            "\nSHORTCUT: Shift + Launch or Doubleclick"
        )

        self.addToQuickLaunchAction = QAction("Add To Quick Launch", self)
        self.addToQuickLaunchAction.setIcon(self.parent.icons.quick_launch)
        self.addToQuickLaunchAction.triggered.connect(self.add_to_quick_launch)

        self.addToFavoritesAction = QAction("Add To Favorites", self)
        self.addToFavoritesAction.setIcon(self.parent.icons.favorite)
        self.addToFavoritesAction.triggered.connect(self.add_to_favorites)

        self.removeFromFavoritesAction = QAction("Remove From Favorites", self)
        self.removeFromFavoritesAction.setIcon(self.parent.icons.favorite)
        self.removeFromFavoritesAction.triggered.connect(self.remove_from_favorites)

        if self.parent_widget is not None:
            self.addToFavoritesAction.setVisible(False)
        else:
            self.removeFromFavoritesAction.setVisible(False)

        self.registerExtentionAction = QAction("Register Extension")
        self.registerExtentionAction.setToolTip("Use this build for .blend files and to display thumbnails")
        self.registerExtentionAction.triggered.connect(self.register_extension)

        self.createShortcutAction = QAction("Create Shortcut")
        self.createShortcutAction.triggered.connect(self.create_shortcut)

        self.showBuildFolderAction = QAction("Show Build Folder")
        self.showBuildFolderAction.setIcon(self.parent.icons.folder)
        self.showBuildFolderAction.triggered.connect(self.show_build_folder)

        config_path = self.make_portable_path()

        self.showConfigFolderAction = QAction(
            "Show Portable Config Folder" if config_path.is_dir() else "Show Config Folder"
        )
        self.showConfigFolderAction.setIcon(self.parent.icons.folder)
        self.showConfigFolderAction.triggered.connect(self.show_config_folder)

        self.createSymlinkAction = QAction("Create Symlink")
        self.createSymlinkAction.triggered.connect(self.create_symlink)

        self.installTemplateAction = QAction("Install Template")
        self.installTemplateAction.triggered.connect(self.install_template)

        self.makePortableAction = QAction("Unmake Portable" if config_path.is_dir() else "Make Portable")
        self.makePortableAction.triggered.connect(self.make_portable)

        self.makePortableAction = QAction("Copy Build Hash")
        self.makePortableAction.triggered.connect(self.copy_build_hash)

        self.debugMenu = BaseMenuWidget("Debug", parent=self)
        self.debugMenu.setFont(self.parent.font_10)

        self.debugLogAction = QAction("Debug Log")
        self.debugLogAction.triggered.connect(lambda: self.launch(exe="blender_debug_log.cmd"))
        self.debugFactoryStartupAction = QAction("Factory Startup")
        self.debugFactoryStartupAction.triggered.connect(lambda: self.launch(exe="blender_factory_startup.cmd"))
        self.debugGpuTemplateAction = QAction("Debug GPU")
        self.debugGpuTemplateAction.triggered.connect(lambda: self.launch(exe="blender_debug_gpu.cmd"))
        self.debugGpuGWTemplateAction = QAction("Debug GPU Glitch Workaround")
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
        self.menu.addMenu(self.debugMenu)

        if self.parent_widget is not None:
            self.renameBranchAction = QAction("Rename Branch")
            self.renameBranchAction.triggered.connect(self.rename_branch)
            self.menu.addAction(self.renameBranchAction)

        self.menu.addSeparator()

        if get_platform() == "Windows":
            self.menu.addAction(self.registerExtentionAction)

        self.menu.addAction(self.createShortcutAction)
        self.menu.addAction(self.createSymlinkAction)
        self.menu.addAction(self.installTemplateAction)
        self.menu.addAction(self.makePortableAction)
        self.menu.addSeparator()

        if self.branch in {"stable", "lts", "bforartists", "daily"}:
            self.menu.addAction(self.showReleaseNotesAction)
        else:
            regexp = re.compile(r"D\d{5}")

            if regexp.search(self.branch):
                self.showReleaseNotesAction.setText("Show Patch Details")
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

        self.initialized.emit()

    def context_menu(self):
        if self.is_damaged:
            return

        self.update_delete_action(self.hovering_and_shifting)
        self.update_config_action(self.hovering_and_shifting)

        if len(self.list_widget.selectedItems()) > 1:
            self.menu_extended.trigger()
            return

        self.createSymlinkAction.setEnabled(True)
        link_path = Path(get_library_folder()) / "bl_symlink"
        link = link_path.as_posix()

        if os.path.exists(link) and (os.path.isdir(link) or os.path.islink(link)) and link_path.resolve() == self.link:
            self.createSymlinkAction.setEnabled(False)

        self.menu.trigger()

    @Slot(bool)
    def update_delete_action(self, shifting: bool):
        reverted_behavior = get_default_delete_action() == 1
        delete_from_drive = not reverted_behavior if shifting else reverted_behavior

        if delete_from_drive:
            self.deleteAction.setText("Delete from Drive")
        else:
            self.deleteAction.setText("Send to Trash")

    @Slot(bool)
    def update_config_action(self, shifting: bool):
        config_path = self.make_portable_path()

        if config_path.is_dir() and not shifting:
            self.showConfigFolderAction.setText("Show Portable Config Folder")
        else:
            self.showConfigFolderAction.setText("Show Config Folder")

    def mouseDoubleClickEvent(self, _event):
        if self.build_info is not None and self.hovering_and_shifting:
            self.launch(launch_mode=LaunchOpenLast())

    def mouseReleaseEvent(self, event):
        if event.button == Qt.MouseButton.LeftButton:
            if self.show_new is True:
                self.build_state_widget.setNewBuild(False)
                self.show_new = False

            mod = QApplication.keyboardModifiers()
            if mod not in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier):
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
            if self._hovered and event.modifiers() & Qt.ShiftModifier:
                self.hovering_and_shifting = True
            else:
                self.hovering_and_shifting = False
        return super().eventFilter(obj, event)

    def _shift_hovering(self):
        self.launchButton.set_text("  Previous")
        self._launch_icon = self.launchButton.icon()
        self.launchButton.setIcon(self.parent.icons.file)
        self.launchButton.setFont(self.parent.font_8)

    def _stopped_shift_hovering(self):
        self.launchButton.set_text("Launch")
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
        self.launchButton.set_text("Updating")
        self.launchButton.setEnabled(False)
        self.deleteAction.setEnabled(False)
        self.installTemplateAction.setEnabled(False)
        a = TemplateTask(self.link)
        a.finished.connect(self.install_template_finished)
        self.parent.task_queue.append(a)

    def install_template_finished(self):
        self.launchButton.set_text("Launch")
        self.launchButton.setEnabled(True)
        self.deleteAction.setEnabled(True)
        self.installTemplateAction.setEnabled(True)

    def launch(self, update_selection=False, exe=None, launch_mode: LaunchMode | None = None):
        assert self.build_info is not None
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
            self.makePortableAction.setText("Make Portable")
            self.showConfigFolderAction.setText("Show Config Folder")
        else:
            if _config_path.is_dir():
                _config_path.rename(config_path)
            else:
                config_path.mkdir(parents=False, exist_ok=True)
            self.makePortableAction.setText("Unmake Portable")
            self.showConfigFolderAction.setText("Show Portable Config Folder")

    def make_portable_path(self):
        version = self.build_info.subversion.rsplit(".", 1)[0]

        if version >= "4.2":
            folder_name = "portable"
            config_path = Path(self.link) / folder_name
        else:
            folder_name = "config"
            config_path = Path(self.link) / version / folder_name

        return config_path

    @Slot()
    def copy_build_hash(self):
        QApplication.clipboard().setText(self.build_info.build_hash)

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

        self.branchLabel.show()

    @Slot()
    def rename_branch_rejected(self):
        self.lineEdit.hide()
        self.branchLabel.show()

    def write_build_info(self):
        assert self.build_info is not None
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
            message="Are you sure you want to<br> \
                  delete selected builds?",
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
            self.list_widget.itemWidget(item).remove_from_drive()

    @Slot()
    def remove_from_drive(self, trash=False):
        if self.parent_widget is not None:
            self.parent_widget.remove_from_drive()
            return

        path = Path(get_library_folder()) / self.link
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
            self.list_widget.itemWidget(item).remove_from_drive(trash=True)

    @Slot()
    def send_to_trash(self):
        self.remove_from_drive(trash=True)

    # TODO Clear icon if build in quick launch
    def remover_started(self):
        self.launchButton.set_text("Deleting")
        self.setEnabled(False)
        self.item.setFlags(self.item.flags() & ~Qt.ItemIsSelectable)

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
        assert self.build_info is not None
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
        widget = LibraryWidget(self.parent, item, self.link, self.parent.UserFavoritesListWidget, parent_widget=self)
        if not self.parent.UserFavoritesListWidget.contains_build_info(self.build_info):
            self.parent.UserFavoritesListWidget.insert_item(item, widget)
        self.child_widget = widget

        self.removeFromFavoritesAction.setVisible(True)
        self.addToFavoritesAction.setVisible(False)
        assert self.build_info is not None
        if self.build_info.is_favorite is False:
            self.build_info.is_favorite = True
            self.write_build_info()

    @Slot()
    def remove_from_favorites(self):
        widget = self.parent_widget or self
        assert widget.child_widget is not None
        self.parent.UserFavoritesListWidget.remove_item(widget.child_widget.item)

        widget.child_widget = None
        widget.removeFromFavoritesAction.setVisible(False)
        widget.addToFavoritesAction.setVisible(True)

        assert self.build_info is not None
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
        assert self.build_info is not None
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
        link = (Path(get_library_folder()) / "bl_symlink").as_posix()
        platform = get_platform()

        if platform == "Windows":
            with contextlib.suppress(Exception):
                os.rmdir(link)

            _call(f'mklink /J "{link}" "{target}"')
        elif platform == "Linux":
            if os.path.exists(link) and os.path.islink(link):
                os.unlink(link)

            os.symlink(target, link)

    @Slot()
    def show_folder(self, folder_path: Path):
        if not folder_path:
            logger.debug("Path is empty or not specified.")
            return

        if not os.path.isdir(folder_path):
            logger.error(f"Path {folder_path} do not exist.")
            return

        platform = get_platform()

        if platform == "Windows":
            os.startfile(folder_path.as_posix())
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

        if self.build_info is None:
            PopupWindow(
                title="Warning",
                info_popup=True,
                message="No build information found.",
                icon=PopupIcon.WARNING,
                parent=self.parent,
            ).show()
            return
        version = self.build_info.semversion
        branch = self.build_info.branch
        custom_folder = None

        if branch == "bforartists":
            custom_folder = "bforartists"
            version = self.build_info.bforartist_version_matcher

        if version is None:
            version_str = ""
        else:
            version_str = f"{version.major}.{version.minor}"

        path = Path(get_blender_config_folder(custom_folder) / version_str)
        general_path = Path(get_blender_config_folder(custom_folder))

        if not path.is_dir():
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
