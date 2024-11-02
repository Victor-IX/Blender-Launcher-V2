
from modules.settings import (
    get_scrape_automated_builds,
    get_scrape_bfa_builds,
    get_scrape_stable_builds,
    get_show_bfa_builds,
    get_show_daily_builds,
    get_show_experimental_and_patch_builds,
    get_show_stable_builds,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QListWidget,
    QListWidgetItem,
)
from widgets.repo_visibility_view import RepoUserView


class RepoGroup(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setContentsMargins(0, 0, 0, 0)

        self.stable_repo = RepoUserView(
            "stable",
            "The builds that come from the stable build",
            library=get_show_stable_builds(),
            download=get_scrape_stable_builds(),
            parent=self,
        )
        self.daily_repo = RepoUserView(
            "daily",
            "Builds created every day. They the latest features and bug fixes, but they can be unstable",
            library=get_show_daily_builds(),
            download=get_scrape_automated_builds(),
            parent=self,
        )
        self.experimental_repo = RepoUserView(
            "experimental",
            "These have new features that may end up in official Blender releases. They can be unstable.",
            library=get_show_experimental_and_patch_builds(),
            download=get_scrape_automated_builds(),
            parent=self,
        )
        self.patch_repo = RepoUserView(
            "patch",
            "Patch based builds",
            library=get_show_experimental_and_patch_builds(),
            download=get_scrape_automated_builds(),
            parent=self,
        )
        self.bforartists_repo = RepoUserView(
            "bforartists",
            "A popular fork of Blender with the goal of improving the UI.",
            library=get_show_bfa_builds(),
            download=get_scrape_bfa_builds(),
            parent=self,
        )

        self.exp_and_patch_groups = QButtonGroup()
        self.exp_and_patch_groups.setExclusive(False)
        self.experimental_repo.add_library_to_group(self.exp_and_patch_groups)
        self.patch_repo.add_library_to_group(self.exp_and_patch_groups)

        self.automated_groups = QButtonGroup()
        self.automated_groups.setExclusive(False)
        self.daily_repo.add_downloads_to_group(self.automated_groups)
        self.experimental_repo.add_downloads_to_group(self.automated_groups)
        self.patch_repo.add_downloads_to_group(self.automated_groups)

        self.repos = [
            self.stable_repo,
            self.daily_repo,
            self.experimental_repo,
            self.patch_repo,
            self.bforartists_repo,
        ]

        for widget in self.repos:
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)  # type: ignore
            self.addItem(item)
            self.setItemWidget(item, widget)

    def total_height(self):
        return sum(r.height() for r in self.repos)
