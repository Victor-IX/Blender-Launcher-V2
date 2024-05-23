from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QHBoxLayout, QSpinBox, QWidget
from semver import Version


class SemVersionEdit(QWidget):
    major_changed = pyqtSignal(int)
    minor_changed = pyqtSignal(int)
    patch_changed = pyqtSignal(int)
    version_changed = pyqtSignal(Version)

    def __init__(self, v: Version | None = None, parent=None, use_patch=True):
        super().__init__(parent)
        if v is None:
            v = Version(3, 0, 0)

        self.version = v
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.major = QSpinBox(self)
        self.major.setValue(v.major)
        self.major.valueChanged.connect(self.major_changed.emit)

        self.minor = QSpinBox(self)
        self.minor.setValue(v.minor)
        self.minor.valueChanged.connect(self.minor_changed.emit)

        self.patch = QSpinBox(self)
        self.patch.setValue(v.patch)
        self.patch.valueChanged.connect(self.patch_changed.emit)
        if not use_patch:
            self.patch.hide()

        layout.addWidget(self.major)
        layout.addWidget(self.minor)
        layout.addWidget(self.patch)

        self.major_changed.connect(self._update_version)
        self.minor_changed.connect(self._update_version)
        self.patch_changed.connect(self._update_version)

    @pyqtSlot()
    def _update_version(self):
        self.version = Version(
            self.major.value(),
            self.minor.value(),
            self.patch.value(),
        )
        self.version_changed.emit(self.version)
