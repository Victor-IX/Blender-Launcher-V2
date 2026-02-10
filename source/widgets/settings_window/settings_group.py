from collections.abc import Callable
from typing import TYPE_CHECKING, Self, TypeVar

from i18n import t
from modules.icons import Icons
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
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
        self._contents_widget = QWidget(self)
        self.contents = QFormLayout()
        self.contents.setSpacing(1)
        self._contents_widget.setLayout(self.contents)

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

        self._layout.addWidget(self._contents_widget, 1, 0, 1, 2)

        self._widget = None
        self._collapsed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, _type, _value, _traceback):
        pass

    def __add_tooltip(self, label: str, widget: QWidget):
        if tt := _check_for_tooltip(label):
            widget.setToolTip(tt)

    def add_checkbox(
        self,
        label: str,
        *,
        default: bool,
        setter: Callable[[bool], None],
    ) -> QCheckBox:
        btn = QCheckBox(t(label), parent=self)
        self.__add_tooltip(label, btn)
        btn.setChecked(default)
        btn.clicked.connect(setter)
        self.contents.addWidget(btn)
        return btn

    def add_spin(
        self,
        label: str,
        *,
        default: int,
        setter: Callable[[int], None],
        min_: int | None = None,
        max_: int | None = None,
    ) -> QSpinBox:
        lb = QLabel(t(label), parent=self)
        self.__add_tooltip(label, lb)
        spin = QSpinBox(parent=self)
        spin.setValue(default)
        spin.valueChanged.connect(setter)

        if min_ is not None:
            spin.setMinimum(min_)
        if max_ is not None:
            spin.setMaximum(max_)

        layout = QHBoxLayout()
        layout.addWidget(lb)
        layout.addWidget(spin)
        self.contents.addRow(layout)
        return spin

    def add_button(
        self,
        label: str,
        *,
        clicked: Callable[[], None],
        label_kwargs: dict | None = None,
    ) -> QPushButton:
        btn = QPushButton(t(label, **(label_kwargs or {})), parent=self)
        self.__add_tooltip(label, btn)
        btn.clicked.connect(clicked)
        self.contents.addWidget(btn)
        return btn

    def add_label(self, label: str) -> QLabel:
        lb = QLabel(t(label), parent=self)
        self.__add_tooltip(label, lb)
        self.contents.addWidget(lb)
        return lb

    _W = TypeVar("_W", bound=QWidget)
    def add(self, widget: _W) -> _W:
        self.contents.addWidget(widget)
        return widget

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
        assert self._widget is not None
        self._widget.hide()
        self.collapse_button.setIcon(self._uncollapse_icon)
        self._collapsed = True
        self.collapsed.emit(True)

        if self.parent():
            self.parent().updateGeometry()

    @Slot()
    def uncollapse(self):
        assert self._widget is not None
        self._widget.show()
        self.collapse_button.setIcon(self._collapse_icon)
        self._collapsed = False
        self.collapsed.emit(False)

        if self.parent():
            self.parent().updateGeometry()


def _check_for_tooltip(s: str) -> str | None:
    key = s + "_tooltip"
    tl = t(key)
    if tl == key:
        return None
    else:
        return tl
