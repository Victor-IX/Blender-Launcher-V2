from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QTabBar


class BaseToolBoxWidget(QTabBar):
    tab_changed = Signal(int)
    branch_changed = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ = parent
        self.tab_to_branch: dict[int, tuple[str, ...]] = {}

        self.setContentsMargins(0, 0, 0, 0)
        self.setShape(QTabBar.Shape.RoundedWest)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Minimum)
        self.setExpanding(False)
        self.setProperty("West", True)
        self.setDrawBase(False)
        self.currentChanged.connect(self.current_changed)

    def add_tab(self, name: str, branch: str | tuple[str, ...]):
        self.addTab(name)
        if isinstance(branch, str):
            branch = (branch,)
        index = self.count() - 1
        self.tab_to_branch[index] = branch

    def current_changed(self, i):
        self.tab_changed.emit(i)
        branch = self.tab_to_branch.get(i, ())
        if branch:
            self.branch_changed.emit(branch)

    def current_branch(self):
        return self.tab_to_branch.get(self.currentIndex(), ())

    def update_visibility(self, idx: int, b: bool):
        self.setTabVisible(idx, b)
        self.setTabEnabled(idx, b)
        self.hide()
        self.show()
