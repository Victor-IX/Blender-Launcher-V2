from collections.abc import Callable
from enum import Enum
from typing import TypeVar

from i18n import t
from modules.icons import Icons
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSpinBox,
    QWidget,
)


def _check_for_tooltip(s: str) -> str | None:
    key = s + "_tooltip"
    tl = t(key)
    if tl == key:
        return None
    else:
        return tl


def _add_tooltip(label: str, widget: QWidget):
    if tt := _check_for_tooltip(label):
        widget.setToolTip(tt)


class GroupOrientation(Enum):
    Horizontal = 0
    Vertical = 1


class GroupContents(QWidget):
    def __init__(self, orientation: GroupOrientation, parent=None, margin: bool = True):
        super().__init__(parent)
        self.contents: QHBoxLayout | QFormLayout
        if orientation == GroupOrientation.Horizontal:
            self.contents = QHBoxLayout(self)
        else:
            self.contents = QFormLayout(self)
            self.contents.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            self.contents.setFormAlignment(Qt.AlignmentFlag.AlignHCenter)
        if not margin:
            self.contents.setContentsMargins(0, 0, 0, 0)

    def add_checkbox(
        self,
        label: str,
        *,
        default: bool,
        setter: Callable[[bool], None],
    ) -> QCheckBox:
        btn = QCheckBox(t(label), parent=self)
        _add_tooltip(label, btn)
        btn.setChecked(default)
        btn.clicked.connect(setter)
        return self.add(btn)

    def add_spin(
        self,
        label: str | None,
        *,
        default: int,
        setter: Callable[[int], None],
        min_: int | None = None,
        max_: int | None = None,
    ) -> QSpinBox:
        spin = QSpinBox(parent=self)
        spin.setValue(default)
        spin.valueChanged.connect(setter)

        if min_ is not None:
            spin.setMinimum(min_)
        if max_ is not None:
            spin.setMaximum(max_)

        return self.add(spin, label)

    def add_double_spin(
        self,
        label: str,
        *,
        default: float,
        setter: Callable[[float], None],
        min_: float | None = None,
        max_: float | None = None,
        step: float | None = None,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(parent=self)
        spin.setValue(default)
        spin.valueChanged.connect(setter)
        if min_ is not None:
            spin.setMinimum(min_)
        if max_ is not None:
            spin.setMaximum(max_)
        if step is not None:
            spin.setSingleStep(step)
        return self.add(spin, label)

    def add_button(
        self,
        label: str,
        *,
        clicked: Callable[[], None],
        label_kwargs: dict | None = None,
    ) -> QPushButton:
        btn = QPushButton(t(label, **(label_kwargs or {})), parent=self)
        _add_tooltip(label, btn)
        btn.clicked.connect(clicked)
        self.contents.addWidget(btn)
        return self.add(btn)

    def add_label(self, label: str) -> QLabel:
        return self.add(self._label(label))

    _W = TypeVar("_W", bound=QWidget)

    def add(self, widget: _W, label: str | None = None) -> _W:
        if label is not None:
            if isinstance(self.contents, QFormLayout):
                self.contents.addRow(self._label(label), widget)
            else:
                layout = QHBoxLayout()
                layout.addWidget(self._label(label))
                layout.addWidget(widget)
                self.contents.addLayout(layout)
        else:
            if isinstance(self.contents, QFormLayout):
                self.contents.addRow(widget)
            else:
                self.contents.addWidget(widget)
        return widget

    def hgroup(self, label: str | None, margin=False) -> "GroupContents":
        grp = GroupContents(GroupOrientation.Horizontal, parent=self, margin=margin)

        if isinstance(self.contents, QFormLayout):
            if label is not None:
                lbl = QLabel(t(label), self)
                self.contents.addRow(lbl, grp)
            else:
                self.contents.addRow(grp)
            return grp

        layout = QHBoxLayout()
        if label is not None:
            lbl = QLabel(t(label), self)
            layout.addWidget(lbl)
        layout.addWidget(grp)
        self.contents.addLayout(layout)

        return grp

    def vgroup(self, label: str | None, margin=False) -> "GroupContents":
        grp = GroupContents(GroupOrientation.Vertical, parent=self, margin=margin)
        if label is not None:
            self.add(QLabel(t(label), self))
        self.add(grp)
        return grp

    def checked_hgroup(
        self,
        label: str,
        default: bool,
        setter: Callable[[bool], None],
        margin=False,
    ) -> "GroupContents":
        grp = GroupContents(GroupOrientation.Horizontal, parent=self, margin=margin)
        btn = QCheckBox(t(label), self)
        btn.setChecked(default)
        btn.clicked.connect(setter)

        def checked(state: Qt.CheckState):
            grp.setEnabled(state == state.Checked)

        btn.checkStateChanged.connect(checked)

        grp.setEnabled(default)
        if isinstance(self.contents, QFormLayout):
            self.contents.addRow(btn, grp)
        else:
            layout = QHBoxLayout()
            layout.addWidget(btn)
            layout.addWidget(grp)
            self.contents.addLayout(layout)

        return grp

    def checked_vgroup(
        self,
        label: str,
        default: bool,
        setter: Callable[[bool], None],
        margin=False,
    ) -> "GroupContents":
        grp = GroupContents(GroupOrientation.Vertical, parent=self, margin=margin)
        btn = QCheckBox(t(label), self)
        btn.setChecked(default)
        btn.clicked.connect(setter)

        def checked(state: Qt.CheckState):
            grp.setEnabled(state == state.Checked)

        btn.checkStateChanged.connect(checked)

        grp.setEnabled(default)
        self.add(btn)
        self.add(grp)
        return grp

    def _label(self, label: str) -> QLabel:
        lb = QLabel(t(label), parent=self)
        _add_tooltip(label, lb)
        return lb

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        pass


class SettingsGroup(QFrame):
    collapsed = Signal(bool)
    checked = Signal(bool)

    def __init__(
        self,
        label: str,
        *,
        checkable=False,
        icons: Icons | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.form = parent
        self.setContentsMargins(0, 0, 0, 0)
        # self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setProperty("SettingsGroup", True)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self.contents = GroupContents(GroupOrientation.Vertical, self)

        if icons is None:
            icons = Icons.get()

        self._collapse_icon = icons.expand_less
        self._uncollapse_icon = icons.expand_more

        self.collapse_button = QPushButton(parent)
        self.collapse_button.setProperty("CollapseButton", True)
        self.collapse_button.setMaximumSize(20, 20)
        self.collapse_button.setIcon(self._collapse_icon)
        self.collapse_button.clicked.connect(self.toggle)
        self._checkable = checkable

        self._layout.addWidget(self.collapse_button, 0, 0, 1, 1)

        if checkable:
            self.checkbutton = QCheckBox(self)
            self.label = None
            self.checkbutton.setText(label)
            self.checkbutton.clicked.connect(self.checked.emit)
            self._layout.addWidget(self.checkbutton, 0, 1, 1, 1)

        else:
            self.checkbutton = None
            self.label = QLabel(f" {label}")
            self._layout.addWidget(self.label, 0, 1, 1, 1)

        self._layout.addWidget(self.contents, 1, 0, 1, 2)

        self._widget = None
        self._collapsed = False

    def __enter__(self) -> GroupContents:
        return self.contents

    def __exit__(self, _type, _value, _traceback):
        pass

    @Slot(QWidget)
    def setWidget(self, w: QWidget):
        if self._widget == w:
            return

        if self._widget is not None:
            self._layout.removeWidget(self._widget)
        self._widget = w
        self._layout.addWidget(self._widget, 2, 0, 1, 2)

    @Slot(QLayout)
    def setLayout(self, layout: QLayout):
        if self._widget is not None:
            self._layout.removeWidget(self._widget)
        self._widget = QWidget()
        self._widget.setLayout(layout)
        self._layout.addWidget(self._widget, 2, 0, 1, 2)

    @Slot(bool)
    def set_collapsed(self, b: bool):
        if b and not self._collapsed:
            self.collapse()
            self._collapsed = True
        elif self._collapsed:
            self.uncollapse()
            self._collapsed = False

    @Slot()
    def toggle(self):
        self.set_collapsed(not self._collapsed)

    @Slot()
    def collapse(self):
        if self._widget is not None:
            self._widget.hide()
            self.collapse_button.setIcon(self._uncollapse_icon)
            self._collapsed = True
            self.collapsed.emit(True)
        self.contents.hide()

        if self.parent():
            self.parent().updateGeometry()

    @Slot()
    def uncollapse(self):
        if self._widget is not None:
            self._widget.show()
            self.collapse_button.setIcon(self._collapse_icon)
            self._collapsed = False
            self.collapsed.emit(False)

        self.contents.show()

        if self.parent():
            self.parent().updateGeometry()
