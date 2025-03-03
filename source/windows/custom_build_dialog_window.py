from __future__ import annotations

import datetime
import logging
import os
from enum import Enum
from typing import TYPE_CHECKING

from modules._platform import get_platform
from modules.build_info import BuildInfo, ReadBuildTask
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QDateTimeEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from widgets.lintable_line_edit import LintableLineEdit
from windows.base_window import BaseWindow

if TYPE_CHECKING:
    from pathlib import Path

    from windows.main_window import BlenderLauncher


class PopupIcon(Enum):
    WARNING = 1
    INFO = 2


class CustomBuildDialogWindow(BaseWindow):
    accepted = Signal(BuildInfo)
    cancelled = Signal()

    def __init__(
        self,
        parent: BlenderLauncher,
        path: Path,
        old_build_info: BuildInfo | None = None,
    ):
        super().__init__(parent=parent)
        self.parent_ = parent
        self.path = path

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(160, 60)

        policy = QSizePolicy(
            QSizePolicy.MinimumExpanding,
            QSizePolicy.MinimumExpanding,
        )
        policy.setHorizontalStretch(0)
        policy.setVerticalStretch(0)
        policy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(policy)

        self.central_widget = QWidget(self)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(6, 6, 6, 6)
        self.central_layout.setSpacing(0)
        self.setCentralWidget(self.central_widget)
        self.setWindowTitle("Build Entry Creator")

        self.text_label = QLabel(f"Create new build for: {path.relative_to(path.parent.parent)!s}")
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self.accept_button = QPushButton("Accept")
        self.accept_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")

        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)

        if self.accept_button.sizeHint().width() > self.cancel_button.sizeHint().width():
            width = self.accept_button.sizeHint().width()
        else:
            width = self.cancel_button.sizeHint().width()

        self.accept_button.setFixedWidth(width + 16)
        self.cancel_button.setFixedWidth(width + 16)

        self.accept_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.cancel)

        self.button_layout.addWidget(self.accept_button, alignment=Qt.AlignmentFlag.AlignRight, stretch=1)
        self.button_layout.addWidget(self.cancel_button)

        platform = get_platform()

        # get list of executable files in `path`
        if platform == "Windows":
            executables = [
                str(file.relative_to(path)) for file in path.iterdir() if file.is_file() and file.suffix == ".exe"
            ]
        else:
            executables = [
                str(file.relative_to(path)) for file in path.iterdir() if file.is_file() and os.access(file, os.X_OK)
            ]
        completer = QCompleter(executables, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        logging.debug(f"Detected executables: {executables}")

        def _red_asterisk():
            label = QLabel("* ", self)
            label.setStyleSheet("color: red;")

            return label

        self.executable_label = QLabel("Executable name: ")
        self.executable_choice = LintableLineEdit(self)

        self.executable_choice.setCompleter(completer)
        self.executable_choice.textChanged.connect(self.check_executable_choice)
        self.executable_choice.setPlaceholderText("blender, bforartists, etc.")
        self.exe_is_valid = False

        executable_layout = QHBoxLayout()
        executable_layout.addWidget(_red_asterisk())
        executable_layout.addWidget(self.executable_label)
        executable_layout.addWidget(self.executable_choice)

        self.auto_detect_button = QPushButton(self)
        self.auto_detect_button.clicked.connect(self.auto_detect_info)
        self.auto_detect_button.setText("Auto-detect information")
        self.auto_detect_button.setEnabled(False)

        # Excerpt from BuildInfo
        # @classmethod
        # def from_dict(cls, path: Path, blinfo: dict):
        #     return cls(
        #         path.as_posix(),
        #         blinfo["subversion"],
        #         blinfo["build_hash"],
        #         blinfo["commit_time"],
        #         blinfo["branch"],
        #         blinfo["custom_name"],
        #         blinfo["is_favorite"],
        #         blinfo.get("custom_executable", ""),
        #     )

        settings_layout = QGridLayout()
        settings_layout.setContentsMargins(0, 0, 0, 0)

        def row_factory(layout: QGridLayout):
            offset = 0

            def _add_row(widget: QWidget, text: str = "", asterisk=False):
                nonlocal offset

                if asterisk:
                    layout.addWidget(_red_asterisk(), offset, 0, 1, 1)

                if text:
                    label = QLabel(text, self)
                    layout.addWidget(label, offset, 1, 1, 1)
                layout.addWidget(widget, offset, 2, 1, 1)
                offset += 1

            return _add_row

        add_row = row_factory(settings_layout)

        self.subversion_edit = QLineEdit(self)
        self.hash_edit = QLineEdit(self)
        self.commit_time = QDateTimeEdit(self)
        self.commit_time.setCalendarPopup(True)
        self.branch_edit = QLineEdit(self)
        self.custom_name = QLineEdit(self)
        self.favorite = QCheckBox(self)

        add_row(self.subversion_edit, "Subversion: ")
        add_row(self.hash_edit, "Build hash: ")
        add_row(self.commit_time, "Commit time: ")
        add_row(self.branch_edit, "Branch name: ")
        add_row(self.custom_name, "Custom name: ")
        add_row(self.favorite, "Favorite: ")

        # Label
        self.central_layout.addWidget(self.text_label)
        self.central_layout.addSpacing(10)

        # Build Settings
        self.central_layout.addLayout(executable_layout)
        self.central_layout.addWidget(self.auto_detect_button)
        self.central_layout.addLayout(settings_layout)

        # Buttons
        self.central_layout.addLayout(self.button_layout)

        if old_build_info:
            self.load_from_build_info(old_build_info)

        self.show()

    def current_binfo(self):
        return BuildInfo(
            str(self.path),
            self.subversion_edit.text(),
            self.hash_edit.text(),
            self.commit_time.dateTime().toPython(),
            self.branch_edit.text(),
            self.custom_name.text(),
            self.favorite.isChecked(),
            self.executable_choice.text(),
        )

    def accept(self):
        # create build_info

        build_info = self.current_binfo()

        self.accepted.emit(build_info)
        self.close()

    def cancel(self):
        self.cancelled.emit()
        self.close()

    def check_executable_choice(self):
        p = self.path / self.executable_choice.text()
        if os.access(p, os.X_OK):
            self.executable_choice.set_valid(True)
            self.exe_is_valid = True
        else:
            self.executable_choice.set_valid(False)
            self.exe_is_valid = False

        is_chosen = bool(self.executable_choice.text())
        self.auto_detect_button.setEnabled(is_chosen)
        self.accept_button.setEnabled(is_chosen)

    def auto_detect_info(self):
        a = ReadBuildTask(
            self.path,
            info=self.current_binfo(),
            auto_write=False,
        )
        a.finished.connect(self.load_from_build_info)
        a.failure.connect(self.auto_detect_failed)
        self.parent_.task_queue.append(a)
        self.auto_detect_button.setEnabled(False)

    def load_from_build_info(self, binfo: BuildInfo):
        logging.info(binfo)

        if not self.executable_choice.text():
            self.executable_choice.setText(binfo.custom_executable)

        if not self.subversion_edit.text():
            self.subversion_edit.setText(str(binfo.subversion))
        if not self.hash_edit.text():
            self.hash_edit.setText(binfo.build_hash)

        self.commit_time.setDateTime(binfo.commit_time)

        if not self.branch_edit.text():
            self.branch_edit.setText(binfo.branch)

        if not self.custom_name.text():
            self.custom_name.setText(binfo.custom_name)

        self.auto_detect_button.setEnabled(True)

    def auto_detect_failed(self):
        self.auto_detect_button.setEnabled(True)
