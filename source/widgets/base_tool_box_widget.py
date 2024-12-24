from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget
from widgets.base_list_widget import BaseListWidget
from widgets.base_page_widget import BasePageWidget


class BaseToolBoxWidget(QTabWidget):
    tab_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages = []
        self.parent = parent
        self.list_widgets = set()

        self.setContentsMargins(0, 0, 0, 0)
        self.setTabPosition(QTabWidget.TabPosition.West)
        self.setProperty("West", True)
        self.currentChanged.connect(self.current_changed)

    def add_page_widget(self, page_widget: BasePageWidget, page_name) -> BaseListWidget:
        self.pages.append(page_widget)
        self.addTab(page_widget, page_name)
        self.list_widgets.add(page_widget.list_widget)
        return page_widget.list_widget

    def current_changed(self, i):
        self.tab_changed.emit(i)
