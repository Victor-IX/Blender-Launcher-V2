from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from modules.version_matcher import BasicBuildInfo, VersionSearchQuery
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QAbstractItemView, QFrame, QListWidget, QListWidgetItem
from widgets.base_build_widget import BaseBuildWidget
from widgets.library_widget import LibraryWidget

if TYPE_CHECKING:
    from modules.build_info import BuildInfo
    from widgets.base_page_widget import BasePageWidget


_WT = TypeVar("_WT", bound=BaseBuildWidget)


class BaseListWidget(Generic[_WT], QListWidget):
    def __init__(self, parent: BasePageWidget, extended_selection=False):
        super().__init__(parent)
        self.parent: BasePageWidget = parent
        self.page = parent
        self.tab_filter = VersionSearchQuery.any()
        self.user_given_searcher = None

        self.widgets: set[_WT] = set()
        self._query_cache: dict[VersionSearchQuery, set[_WT]] = {}
        self._binfos_cache: tuple[dict[BasicBuildInfo, list[_WT]], set[_WT]] | None = None
        self.metrics = QFontMetrics(self.font())

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
        if self.user_given_searcher is not None:
            q |= self.user_given_searcher
        return q

    def __str__(self):
        widget = [widget.build_info for widget in self.widgets]
        return f"BaseListWidget build info: {widget}"

    def itemWidget(self, item) -> _WT | None:  # type: ignore
        return super().itemWidget(item)

    def add_item(self, item, widget):
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.count_changed()
        self.widgets.add(widget)
        self._binfos_cache = None
        self.update_visibility(item, widget)

    def insert_item(self, item, widget, index=0):
        item.setSizeHint(widget.sizeHint())
        self.insertItem(index, item)
        self.setItemWidget(item, widget)
        self.count_changed()
        self.widgets.add(widget)
        self._binfos_cache = None
        self.update_visibility(item, widget)

    def remove_item(self, item):
        if (w := self.itemWidget(item)) is not None:
            self.widgets.remove(w)
            self._binfos_cache = None
        row = self.row(item)
        self.takeItem(row)
        self.count_changed()

    def count_changed(self):
        self.__show(self.count() > 0)

    def __show(self, b: bool):
        if b:
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
        self._binfos_cache = None
        self._query_cache = {}
        self.count_changed()

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

    def basic_build_infos(self) -> tuple[dict[BasicBuildInfo, list[_WT]], set[_WT]]:
        if self._binfos_cache is not None:
            return self._binfos_cache

        binfo_to_widgets: dict[BasicBuildInfo, list[_WT]] = {}
        unknown_widgets: set[_WT] = set()

        for widget in self.widgets:
            binfo = self.basic_from_widget(widget)
            if binfo is None:
                continue

            if (lst := binfo_to_widgets.get(binfo)) is not None:
                lst.append(widget)
            else:
                binfo_to_widgets[binfo] = [widget]

        self._binfos_cache = (binfo_to_widgets, unknown_widgets)

        return self._binfos_cache

    def get_matching_builds(self, search: VersionSearchQuery):
        if search not in self._query_cache:
            binfo_to_widget, unknown_widgets = self.basic_build_infos()
            # gather all matching widgets
            shown_widgets: set[_WT] = {w for b in search.match(list(binfo_to_widget)) for w in binfo_to_widget[b]}

            # add broken widgets to the results
            shown_widgets |= unknown_widgets

            self._query_cache[search] = shown_widgets

        return self._query_cache[search]

    def update_tab_filter(self, tab_filter: VersionSearchQuery):
        self.tab_filter = tab_filter
        self.update_all_visibility()

    def update_all_visibility(self):
        visible_builds = self.get_matching_builds(self.query)

        hidden_widgets = self.widgets - visible_builds

        for widget in visible_builds:
            widget.item.setHidden(False)
        for widget in hidden_widgets:
            widget.item.setHidden(True)

        self.__show(len(hidden_widgets) != len(self.items()))

    def update_visibility(self, item: QListWidgetItem, widget: _WT | None = None):
        if widget is None and (widget := self.itemWidget(item)) is None:
            return
        if (binfo := self.basic_from_widget(widget)) is None:
            return

        q = self.query
        success = bool(q.match([binfo]))
        if (s := self._query_cache.get(q)) is not None:
            if success:
                s |= {widget}
            else:
                s -= {widget}

        item.setHidden(not success)

    def clear_by_branch(self, branch: str):
        widgets_to_remove = [widget for widget in self.widgets if widget.build_info.branch == branch]
        for widget in widgets_to_remove:
            items = [self.item(i) for i in range(self.count()) if self.itemWidget(self.item(i)) == widget]
            for item in items:
                self.remove_item(item)
