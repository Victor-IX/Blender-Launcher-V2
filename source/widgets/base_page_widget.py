from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic

from modules.settings import get_list_sorting_type, set_list_sorting_type
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from widgets.base_list_widget import BaseListWidget, W


class SortingType(Enum):
    DATETIME = 1
    VERSION = 2


@dataclass(frozen=True)
class Column:
    label: str
    sortby: SortingType | None = None
    width: int | None = None
    spacing: tuple[int, int] | None = None
    stretch: bool = False
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter


@dataclass(frozen=True)
class PageSchema:
    """The basic structure of a page, including the expected columns and the empty text."""

    name: str
    columns: tuple[Column, ...]
    show_reload: bool = False
    empty_text: str = "Nothing to show yet"
    extended_selection: bool = False

    def with_name(self, name: str):
        return self.__class__(
            name,
            self.columns,
            self.show_reload,
            self.empty_text,
            self.extended_selection,
        )


class BasePageWidget(QWidget, Generic[W]):
    reload_pressed = pyqtSignal()

    def __init__(
        self,
        parent,
        page_schema: PageSchema,
    ):
        super().__init__(parent)
        self.name = page_schema.name

        self.sort_order_asc = True

        self.layout: QVBoxLayout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Placeholder Widget
        self.PlaceholderWidget = QWidget()
        self.PlaceholderWidget.setProperty("ToolBoxWidget", True)
        self.PlaceholderLayout = QVBoxLayout(self.PlaceholderWidget)
        self.PlaceholderLayout.setContentsMargins(0, 0, 0, 0)

        self.InfoPixmap = QPixmap(":resources/icons/info.svg")
        self.InfoPixmapLabel = QLabel()
        self.InfoPixmapLabel.setScaledContents(True)
        self.InfoPixmapLabel.setFixedSize(32, 32)
        self.InfoPixmapLabel.setPixmap(self.InfoPixmap)

        self.InfoLabelLayout = QHBoxLayout()
        self.InfoLabelLayout.setContentsMargins(0, 0, 0, 6)
        self.InfoLabel = QLabel(page_schema.empty_text)
        self.InfoLabelLayout.addWidget(self.InfoLabel)

        self.list_widget: BaseListWidget[W] = BaseListWidget(self, extended_selection=page_schema.extended_selection)
        self.list_widget.hide()

        self.InfoLayout = QHBoxLayout()
        self.InfoLayout.setContentsMargins(0, 0, 0, 0)

        self.InfoLayout.addStretch()
        self.InfoLayout.addWidget(self.InfoPixmapLabel)
        self.InfoLayout.addLayout(self.InfoLabelLayout)
        self.InfoLayout.addStretch()

        self.PlaceholderLayout.addStretch()
        self.PlaceholderLayout.addLayout(self.InfoLayout)

        if page_schema.show_reload is True:
            self.ReloadBtn = QPushButton("Reload")
            self.ReloadBtn.setToolTip("Reload from disk")
            self.ReloadBtn.clicked.connect(self.reload_pressed.emit)

            self.ReloadBtnLayout = QHBoxLayout()
            self.ReloadBtnLayout.addStretch()
            self.ReloadBtnLayout.addWidget(self.ReloadBtn)
            self.ReloadBtnLayout.addStretch()

            self.PlaceholderLayout.addLayout(self.ReloadBtnLayout)

        self.PlaceholderLayout.addStretch()

        self.header_schema = page_schema
        self.sorter_mapping: dict[SortingType, QPushButton] = {}

        # Header Widget
        self.HeaderWidget = QWidget()
        self.HeaderWidget.hide()
        self.HeaderWidget.setProperty("ToolBoxWidget", True)
        self.HeaderLayout = QHBoxLayout(self.HeaderWidget)
        self.HeaderLayout.setContentsMargins(2, 0, 0, 0)
        self.HeaderLayout.setSpacing(2)

        if page_schema.show_reload is True:
            self.fakeLabel = QPushButton("Reload")
            self.fakeLabel.setToolTip("Reload from disk")
            self.fakeLabel.setProperty("ListHeader", True)
            self.fakeLabel.clicked.connect(self.reload_pressed.emit)
        else:
            self.fakeLabel = QLabel()
        self.fakeLabel.setFixedWidth(85)
        self.HeaderLayout.addWidget(self.fakeLabel)

        for column in self.header_schema.columns:
            if column.spacing is not None and column.spacing[0] > 0:
                self.HeaderLayout.addSpacing(column.spacing[0])

            if column.sortby is not None:
                w = QPushButton(column.label, self)
                w.setCheckable(True)
                self.sorter_mapping[column.sortby] = w

                @pyqtSlot()
                def setter(_b, column=column):
                    self.set_sorting_type(column.sortby)

                w.clicked.connect(setter)
            else:
                w = QLabel(column.label, self)

                w.setAlignment(column.alignment)
            w.setProperty("ListHeader", True)
            if column.width is not None:
                if column.stretch:
                    w.setMinimumWidth(column.width)
                else:
                    w.setFixedWidth(column.width)

            self.HeaderLayout.addWidget(w, stretch=column.stretch)

            if column.spacing is not None and column.spacing[1] > 0:
                self.HeaderLayout.addSpacing(column.spacing[1])

        # Final layout
        self.layout.addWidget(self.HeaderWidget)
        self.layout.addWidget(self.PlaceholderWidget)
        self.layout.addWidget(self.list_widget)

        self.sorting_type = SortingType(get_list_sorting_type(self.name))
        self.sorting_order = Qt.SortOrder.DescendingOrder
        self.set_sorting_type(self.sorting_type)

    def set_info_label_text(self, text):
        self.InfoLabel.setText(text)

    def set_sorting_type(self, sorting_type):
        if sorting_type == self.sorting_type:
            self.sorting_order = (
                Qt.SortOrder.DescendingOrder
                if self.sorting_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self.sorting_order = Qt.SortOrder.AscendingOrder

        self.sorting_type = sorting_type
        self.list_widget.sortItems(self.sorting_order)

        for st, button in self.sorter_mapping.items():
            button.setChecked(st == sorting_type)

        set_list_sorting_type(self.name, sorting_type)
