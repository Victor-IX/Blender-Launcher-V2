from __future__ import annotations

from datetime import timezone
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QListWidgetItem

if TYPE_CHECKING:
    from semver import Version
    from widgets.base_list_widget import BaseListWidget
    from widgets.download_widget import DownloadWidget
    from widgets.foreign_build_widget import UnrecoBuildWidget
    from widgets.library_widget import LibraryWidget


class BaseListWidgetItem(QListWidgetItem):
    def __init__(self, date=None):
        super().__init__()
        self.date = date

    def listWidget(self) -> BaseListWidget[LibraryWidget | UnrecoBuildWidget | DownloadWidget] | None:
        return super().listWidget()

    def __lt__(self, other):
        soring_type = self.listWidget().parent.sorting_type

        if soring_type.name == "DATETIME":
            return self.compare_datetime(other)
        if soring_type.name == "VERSION":
            return self.compare_version(other)
        return False

    def compare_datetime(self, other):
        if (self.date is None) or (other.date is None):
            return False

        if self.date.tzinfo is None or other.date.tzinfo is None:
            self.date = self.date.replace(tzinfo=timezone.utc)
            other.date = other.date.replace(tzinfo=timezone.utc)

        return self.date > other.date

    def compare_version(self, other):
        list_widget = self.listWidget()

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
