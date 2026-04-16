from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast

from modules.version_matcher import BasicBuildInfo, VersionSearchQuery
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QFrame, QListWidget, QListWidgetItem
from widgets.base_build_widget import BaseBuildWidget
from widgets.library_widget import LibraryWidget

if TYPE_CHECKING:
    from modules.build_info import BuildInfo
    from widgets.base_page_widget import BasePageWidget


_WT = TypeVar("_WT", bound=BaseBuildWidget)


class BaseListWidget(Generic[_WT], QListWidget):
    visible_count_changed = Signal(int)

    def __init__(self, parent: BasePageWidget, extended_selection=False):
        super().__init__(parent)
        self.page: BasePageWidget = parent
        self.tab_filter = VersionSearchQuery.any()
        self.search_filter = None

        self.widgets: set[_WT] = set()
        self._binfos_cache: dict[BasicBuildInfo | None, set[_WT]] = {None: set()}

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setProperty("HideBorder", True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        if extended_selection is True:
            self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    @property
    def query(self) -> VersionSearchQuery:
        q = self.tab_filter
        if self.search_filter is not None:
            q |= self.search_filter
        return q

    def __str__(self):
        widget = [widget.build_info for widget in self.widgets]
        return f"BaseListWidget build info: {widget}"

    def itemWidget(self, item) -> _WT | None:
        return cast("_WT | None", super().itemWidget(item))

    def add_item(self, item, widget):
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.widgets.add(widget)
        self._cache_widget(widget)
        self.update_visibility(item, widget)
        self.visible_count_changed.emit(len(self.widgets))

    def insert_item(self, item, widget, index=0):
        item.setSizeHint(widget.sizeHint())
        self.insertItem(index, item)
        self.setItemWidget(item, widget)
        self.widgets.add(widget)
        self._cache_widget(widget)
        self.update_visibility(item, widget)
        self.visible_count_changed.emit(len(self.widgets))

    def _cache_widget(self, widget):
        self._binfos_cache.setdefault(self.basic_from_widget(widget), set()).add(widget)

    def remove_item(self, item):
        if (w := self.itemWidget(item)) is not None:
            self.widgets.remove(w)
            self._binfos_cache[self.basic_from_widget(w)].remove(w)
        row = self.row(item)
        self.takeItem(row)
        self.visible_count_changed.emit(len(self.widgets))

    def items(self):
        items = []

        for i in range(self.count()):
            item = self.itemWidget(self.item(i))
            items.append(item)

        return items

    def contains_build_info(self, build_info: BuildInfo):
        fsv = build_info.full_semversion
        return any(fsv == widget.build_info.full_semversion for widget in self.widgets)

    def widget_with_blinfo(self, build_info: BuildInfo) -> _WT | None:
        try:
            return next(widget for widget in self.widgets if build_info == widget.build_info)
        except StopIteration:
            return None

    def clear_(self):
        self.clear()
        self.widgets.clear()
        self._binfos_cache = {None: set()}
        self._query_cache = {}
        self.visible_count_changed.emit(0)

    @staticmethod
    def basic_from_widget(widget: _WT) -> BasicBuildInfo | None:
        build_info = widget.build_info
        if build_info.subversion == "0.0.0" and build_info.build_hash == "":
            # likely a template build with BuildInfo.from_blender_path
            return None

        # BuildInfo.branch is an unreliable source of filtering for the major categories,
        # BuildInfo.link is either a URL or a filepath depending on what widget
        # we're storing, so it's not feasible to make assumptions of the foldername
        # just from the link, and some builds branches differ from the folder so we
        # need to categorize the folders separately from branch
        if isinstance(widget, LibraryWidget):
            folder = widget.link.parent.name
        else:
            folder = widget.build_info.branch
        return BasicBuildInfo.from_buildinfo(build_info, folder=folder)

    def get_matching_builds(self, search: VersionSearchQuery) -> list[_WT]:
        binfo_to_widget = self._binfos_cache
        unknown_widgets = binfo_to_widget[None]

        # binfo_to_widget, unknown_widgets = self.basic_build_infos()
        # gather all matching widgets in the order returned by search.match
        matching_binfos = search.match(b for b in binfo_to_widget if b is not None)

        # Flatten matching widgets from binfos
        shown_widgets: list[_WT] = []
        for b in matching_binfos:
            shown_widgets.extend(binfo_to_widget[b])

        # Add broken widgets to the results
        if unknown_widgets:
            shown_widgets.extend(w for w in unknown_widgets if w not in shown_widgets)

        return shown_widgets

    def update_tab_filter(self, tab_filter: VersionSearchQuery):
        self.tab_filter = tab_filter
        self.update_all_visibility()

    def update_search_filter(self, search_filter: VersionSearchQuery | None):
        self.search_filter = search_filter
        self.update_all_visibility()

    def update_all_visibility(self):
        visible_widgets = self.get_matching_builds(self.query)
        visible_set = set(visible_widgets)

        for widget in self.widgets:
            widget.item.setHidden(widget not in visible_set)

        self.visible_count_changed.emit(len(visible_widgets))
        return visible_widgets

    def update_visibility(self, item: QListWidgetItem, widget: _WT | None = None):
        if widget is None and (widget := self.itemWidget(item)) is None:
            return
        if (binfo := self.basic_from_widget(widget)) is None:
            return

        q = self.query
        success = bool(q.match([binfo]))

        item.setHidden(not success)

    def clear_by_branch(self, branch: str):
        widgets_to_remove = [widget for widget in self.widgets if widget.build_info.branch == branch]
        for widget in widgets_to_remove:
            items = [self.item(i) for i in range(self.count()) if self.itemWidget(self.item(i)) == widget]
            for item in items:
                self.remove_item(item)
