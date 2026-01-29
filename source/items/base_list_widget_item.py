from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Generic, TypeVar

from PySide6.QtWidgets import QListWidgetItem
from widgets.base_build_widget import BaseBuildWidget

if TYPE_CHECKING:
    from semver import Version
    from widgets.base_list_widget import BaseListWidget

_WT = TypeVar("_WT", bound=BaseBuildWidget)


class BaseListWidgetItem(QListWidgetItem, Generic[_WT]):
    def __init__(self, date=None):
        super().__init__()
        self.date = date

    def list_widget(self) -> BaseListWidget[_WT]:
        return self.listWidget()  # type: ignore

    def __lt__(self, other):
        sorting_type = self.list_widget().page.sorting_type

        if sorting_type.name == "DATETIME":
            return self.compare_datetime(other)
        if sorting_type.name == "VERSION":
            return self.compare_version(other)
        if sorting_type.name == "LABEL":
            return self.compare_label(other)
        return False

    def compare_datetime(self, other):
        if (self.date is None) or (other.date is None):
            return False

        if self.date.tzinfo is None or other.date.tzinfo is None:
            self.date = self.date.replace(tzinfo=UTC)
            other.date = other.date.replace(tzinfo=UTC)

        return self.date > other.date

    def compare_version(self, other):
        list_widget = self.list_widget()

        this_widget = list_widget.itemWidget(self)
        other_widget = list_widget.itemWidget(other)

        if (
            this_widget is None
            or other_widget is None
            or this_widget.build_info is None
            or other_widget.build_info is None
        ):
            return False

        this_version: Version = this_widget.build_info.semversion
        other_version: Version = other_widget.build_info.semversion

        if this_version == other_version:
            return self.compare_datetime(other)

        return this_version > other_version

    def compare_label(self, other):
        list_widget = self.list_widget()

        this_widget = list_widget.itemWidget(self)
        other_widget = list_widget.itemWidget(other)

        if (
            this_widget is None
            or other_widget is None
            or this_widget.build_info is None
            or other_widget.build_info is None
        ):
            return False

        this_label = this_widget.build_info.display_label
        other_label = other_widget.build_info.display_label

        return this_label < other_label
