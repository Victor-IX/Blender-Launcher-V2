from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from modules.version_matcher import BasicBuildInfo, BInfoMatcher, VersionSearchQuery
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QAbstractItemView, QFrame, QListWidget, QListWidgetItem
from widgets.base_build_widget import BaseBuildWidget

if TYPE_CHECKING:
    from modules.build_info import BuildInfo
    from widgets.base_page_widget import BasePageWidget


_WT = TypeVar("_WT", bound=BaseBuildWidget)


class BaseListWidget(Generic[_WT], QListWidget):
    def __init__(self, parent: BasePageWidget | None = None, extended_selection=False):
        super().__init__(parent)
        self.parent: BasePageWidget | None = parent
        self.search = VersionSearchQuery.any()

        self.widgets: set[_WT] = set()
        self.metrics = QFontMetrics(self.font())

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setProperty("HideBorder", True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        if extended_selection is True:
            self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def __str__(self):
        widget = [widget.build_info for widget in self.widgets]
        return f"BaseListWidget build info: {widget}"

    def itemWidget(self, item) -> _WT | None:  # type: ignore
        return super().itemWidget(item)  # type: ignore[return-value]

    def add_item(self, item, widget):
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.count_changed()
        self.widgets.add(widget)
        self.reevaluate_visibility(item, widget)

    def insert_item(self, item, widget, index=0):
        item.setSizeHint(widget.sizeHint())
        self.insertItem(index, item)
        self.setItemWidget(item, widget)
        self.count_changed()
        self.widgets.add(widget)
        self.reevaluate_visibility(item, widget)

    def remove_item(self, item):
        if (w := self.itemWidget(item)) is not None:
            self.widgets.remove(w)
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

    def widget_with_blinfo(self, build_info: BuildInfo) -> _WT | None:
        try:
            return next(widget for widget in self.widgets if build_info == widget.build_info)
        except StopIteration:
            return None

    def clear_(self):
        self.clear()
        self.widgets.clear()
        self.count_changed()

    def get_matching_builds(self, search: VersionSearchQuery, broken_builds=True):
        binfo_to_widget: dict[BasicBuildInfo, _WT] = {}
        binfos: list[BasicBuildInfo] = []
        unknown_widgets: set[_WT] = set()

        for widget in self.widgets:
            if widget.build_info is not None:
                binfo = BasicBuildInfo.from_buildinfo(widget.build_info)
                binfo_to_widget[binfo] = widget
                binfos.append(binfo)
            else:
                unknown_widgets.add(widget)

        # gather all matching widgets
        shown_widgets: set[_WT] = {binfo_to_widget[b] for b in search.match(list(binfo_to_widget))}

        # add broken widgets to the filter
        if broken_builds:
            shown_widgets |= unknown_widgets

        return shown_widgets

    def update_branch_filter(self, branches: tuple[str, ...]):
        self.search = self.search.with_branch(branches)
        self.update_all_visibility()

    def update_all_visibility(self):
        visible_builds = self.get_matching_builds(self.search)

        hidden_widgets = self.widgets - visible_builds

        for widget in visible_builds:
            widget.item.setHidden(False)
        for widget in hidden_widgets:
            widget.item.setHidden(True)

    def reevaluate_visibility(self, item: QListWidgetItem, widget: _WT | None = None):
        if (widget is None and (widget := self.itemWidget(item)) is None) or widget.build_info is None:
            return
        item.setHidden(not bool(self.search.match([BasicBuildInfo.from_buildinfo(widget.build_info)])))

    def clear_by_branch(self, branch: str):
        widgets_to_remove = [widget for widget in self.widgets if widget.build_info.branch == branch]
        for widget in widgets_to_remove:
            items = [self.item(i) for i in range(self.count()) if self.itemWidget(self.item(i)) == widget]
            for item in items:
                self.remove_item(item)
