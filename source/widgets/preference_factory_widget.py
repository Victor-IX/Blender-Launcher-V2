from enum import Enum
from typing import TYPE_CHECKING

from modules.prefs_info import PreferenceInfo, pref_path_name
from modules.settings import blender_minimum_versions, get_library_folder
from modules.tasks import TaskQueue
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from semver import Version
from widgets.base_build_widget import BaseBuildWidget
from windows.dialog_window import DialogWindow

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class PreferenceFactoryState(Enum):
    READY = 0
    CREATING = 1


class PreferenceFactoryWidget(BaseBuildWidget):
    preference_created = pyqtSignal(PreferenceInfo)

    def __init__(self, parent, list_widget, task_queue: TaskQueue):
        super().__init__(parent=parent)
        self.parent: BlenderLauncher = parent
        self.setAcceptDrops(False)

        self.list_widget = list_widget
        self.task_queue = task_queue
        self.existing_preferences: list[str] = []  # Used to check if the name is already taken

        # This is ugly. I will rework the version listing later to have something dynamic instead of a static list.
        self.blender_versions = [version for version in blender_minimum_versions.keys() if version != "None"]
        self.blender_versions.append("Custom")

        # box should highlight when dragged over
        self.layout: QGridLayout = QGridLayout()
        self.layout.setContentsMargins(2, 2, 0, 2)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.layout)
        self.draw()
        self.update_state(PreferenceFactoryState.READY)

    def draw(self):
        self.creation_button = QPushButton("Create...", self)
        self.creation_button.setFixedWidth(85)
        self.creation_button.setProperty("CreateButton", True)
        self.creation_button.pressed.connect(self.start_creation)
        # self.creation_button.setFixedHeight(60)

        self.name_text_label = QLabel("Preferences name", self)
        self.name_text_label.setFont(self.parent.font_8)
        self.name_text_label.setContentsMargins(2, 0, 0, 0)
        self.name_text_edit = QLineEdit(self)
        self.name_text_edit.textChanged.connect(self.text_changed)

        self.target_version_label = QLabel("target")
        self.target_version_label.setContentsMargins(2, 0, 0, 0)
        self.target_version_label.setFont(self.parent.font_8)
        self.target_version_dropdown = QComboBox()
        self.target_version_dropdown.addItems(self.blender_versions)
        self.target_version_dropdown.setFixedWidth(85)
        self.target_version_dropdown.currentIndexChanged.connect(lambda _: self.update_state(PreferenceFactoryState.CREATING))

        self.custom_target_version_label = QLabel("custom")
        self.custom_target_version_label.setContentsMargins(2, 0, 0, 0)
        self.custom_target_version_label.setFont(self.parent.font_8)
        self.custom_target_version_dial = QDoubleSpinBox()
        self.custom_target_version_dial.setSingleStep(0.1)
        self.custom_target_version_dial.setDecimals(1)
        self.custom_target_version_dial.setFixedWidth(85)

        self.confirm_button = QPushButton("Confirm", self)
        self.confirm_button.setFixedWidth(85)
        self.confirm_button.setProperty("LaunchButton", True)
        self.confirm_button.pressed.connect(self.confirm)
        self.confirm_button.setEnabled(False)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setFixedWidth(85)
        self.cancel_button.setProperty("CancelButton", True)
        self.cancel_button.pressed.connect(self.cancel)

        self.layout.addWidget(self.creation_button, 0, 0, 1, 1)
        self.layout.addWidget(self.name_text_label, 0, 1, 1, 1)
        self.layout.addWidget(self.name_text_edit, 1, 1, 1, 1)
        self.layout.addWidget(self.target_version_label, 0, 2, 1, 1)
        self.layout.addWidget(self.target_version_dropdown, 1, 2, 1, 1)

        self.layout.addWidget(self.custom_target_version_label, 0, 3, 1, 1)
        self.layout.addWidget(self.custom_target_version_dial, 1, 3, 1, 1)
        self.layout.addWidget(self.confirm_button, 0, 4, 2, 1)
        self.layout.addWidget(self.cancel_button, 0, 5, 2, 1)

        self.creation_button.setCursor(Qt.CursorShape.PointingHandCursor)

    @pyqtSlot(PreferenceFactoryState)
    def update_state(self, state: PreferenceFactoryState):
        self.state = state
        self.selected_version = self.target_version_dropdown.currentText()

        if self.selected_version == "Custom" and state == PreferenceFactoryState.CREATING:
            self.custom_target_version_label.show()
            self.custom_target_version_dial.show()
        else:
            self.custom_target_version_label.hide()
            self.custom_target_version_dial.hide()
            self.custom_target_version_dial.setValue(4.2)

        if state == PreferenceFactoryState.READY:
            self.creation_button.show()
            self.name_text_label.hide()
            self.name_text_edit.hide()
            self.name_text_edit.clear()
            self.target_version_label.hide()
            self.target_version_dropdown.hide()

            self.confirm_button.hide()
            self.cancel_button.hide()
        elif state == PreferenceFactoryState.CREATING:
            self.creation_button.hide()
            self.name_text_label.show()
            self.name_text_edit.show()
            self.target_version_label.show()
            self.target_version_dropdown.show()

            self.confirm_button.show()
            self.cancel_button.show()

    def update_existing_prefs(self, existing: list[str]):
        self.existing_preferences = existing

    def start_creation(self):
        self.update_state(PreferenceFactoryState.CREATING)

    def text_changed(self):
        if s := self.name_text_edit.text().strip():
            if s in self.existing_preferences:
                self.name_text_label.setText("Name is already taken!")
            else:
                self.name_text_label.setText("Preferences name")
            self.confirm_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)

    def cancel(self):
        self.update_state(PreferenceFactoryState.READY)

    def confirm(self):
        name = self.name_text_edit.text().strip()
        version = self.target_version_dropdown.currentText()

        if version != "Custom":
            v = float(version)
        else:
            v = self.custom_target_version_dial.value()

        major = int(v)
        if major <= 2:
            # 2.93, 2.79, etc.
            minor = round(v * 100) % 100
        else:
            # 3.0, 4.1, etc.
            minor = round(v * 10) % 100

        target_version = Version(major, minor, 0)
        pref_name = pref_path_name(name)

        info = PreferenceInfo(get_library_folder() / "config" / pref_name, target_version, name)
        # ? Do we need to move this to a task? This should be very fast anyways
        info.write()  # Write the file to disk

        self.preference_created.emit(info)
        self.update_state(PreferenceFactoryState.READY)

    @pyqtSlot()
    def install(self):
        self.create_pressed.emit()
