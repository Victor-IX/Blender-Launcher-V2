from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem
from widgets.base_page_widget import SortingType

if TYPE_CHECKING:
    from semver import Version
    from widgets.base_list_widget import BaseListWidget
    from widgets.preference_widget import PreferenceWidget


class PrefsListWidgetItem(QListWidgetItem):
    def __init__(self, has_info=True):
        super().__init__()
        self.has_info = has_info

    def listWidget(self) -> BaseListWidget[PreferenceWidget] | None:
        return super().listWidget()

    def __lt__(self, other):
        if not self.has_info:
            return self.listWidget().parent.sorting_order == Qt.SortOrder.DescendingOrder
        soring_type = self.listWidget().parent.sorting_type

        if soring_type == SortingType.VERSION:
            return self.compare_version(other)

        return self.compare_name(other)

    def compare_version(self, other):
        list_widget = self.listWidget()
        this_widget = list_widget.itemWidget(self)
        other_widget = list_widget.itemWidget(other)

        if (
            this_widget is None
            or other_widget is None
            or this_widget.info.target_version is None
            or not hasattr(other_widget, "info")
            or other_widget.info.target_version is None
        ):
            return False

        this_version: Version = this_widget.info.target_version
        other_version: Version = other_widget.info.target_version

        if this_version == other_version:
            return self.compare_name(other)

        return this_version > other_version

    def compare_name(self, other):
        list_widget = self.listWidget()
        this_widget = list_widget.itemWidget(self)
        other_widget = list_widget.itemWidget(other)

        if this_widget is None or other_widget is None:
            return False

        return this_widget.info.name < other_widget.info.name
