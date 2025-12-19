from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QAbstractItemView, QListWidget

if TYPE_CHECKING:
    from modules.build_info import BuildInfo
    from widgets.base_build_widget import BaseBuildWidget
    from widgets.base_page_widget import BasePageWidget


class BaseListWidget(QListWidget):
    def __init__(self, parent: BasePageWidget | None = None, extended_selection=False):
        super().__init__(parent)
        self.parent: BasePageWidget | None = parent

        self.widgets = set()
        self.metrics = QFontMetrics(self.font())

        self.setFrameShape(QListWidget.NoFrame)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setProperty("HideBorder", True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        if extended_selection is True:
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def __str__(self):
        widget = [widget.build_info for widget in self.widgets]
        return f"BaseListWidget build info: {widget}"

    def add_item(self, item, widget):
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.count_changed()
        self.widgets.add(widget)

    def insert_item(self, item, widget, index=0):
        item.setSizeHint(widget.sizeHint())
        self.insertItem(index, item)
        self.setItemWidget(item, widget)
        self.count_changed()
        self.widgets.add(widget)

    def remove_item(self, item):
        self.widgets.remove(self.itemWidget(item))
        row = self.row(item)
        self.takeItem(row)
        self.count_changed()

    def count_changed(self):
        if self.count() > 0:
            self.show()
            self.parent.HeaderWidget.show()
            self.parent.PlaceholderWidget.hide()
        else:
            self.hide()
            self.parent.HeaderWidget.hide()
            self.parent.PlaceholderWidget.show()

    def items(self):
        items = []

        for i in range(self.count()):
            item = self.itemWidget(self.item(i))
            items.append(item)

        return items

    def contains_build_info(self, build_info):
        return any(build_info == widget.build_info for widget in self.widgets)

    def widget_with_blinfo(self, build_info: BuildInfo) -> BaseBuildWidget | None:
        try:
            return next(widget for widget in self.widgets if build_info == widget.build_info)
        except StopIteration:
            return None

    def clear_(self):
        self.clear()
        self.widgets.clear()
        self.count_changed()
