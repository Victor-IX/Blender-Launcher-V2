from modules.settings import (
    get_scrape_automated_builds,
    get_scrape_bfa_builds,
    get_scrape_stable_builds,
    get_show_bfa_builds,
    get_show_daily_builds,
    get_show_experimental_and_patch_builds,
    get_show_stable_builds,
)
from PyQt5.QtCore import Qt, pyqtSlot
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
            "Stable",
            "The builds that come from the stable build",
            library=get_show_stable_builds(),
            download=get_scrape_stable_builds(),
            parent=self,
        )
        self.daily_repo = RepoUserView(
            "Daily",
            "Builds created every day. They the latest features and bug fixes, but they can be unstable",
            library=get_show_daily_builds(),
            download=get_scrape_automated_builds(),
            bind_download_to_library=False,
            parent=self,
        )
        self.experimental_repo = RepoUserView(
            "Experimental and Patch",
            "These have new features that may end up in official Blender releases. They can be unstable.",
            library=get_show_experimental_and_patch_builds(),
            download=get_scrape_automated_builds(),
            bind_download_to_library=False,
            parent=self,
        )
        self.bforartists_repo = RepoUserView(
            "Bforartists",
            "A popular fork of Blender with the goal of improving the UI.",
            library=get_show_bfa_builds(),
            download=get_scrape_bfa_builds(),
            parent=self,
        )

        self.daily_repo.library_changed.connect(self.check_if_both_automated_are_disabled)
        self.experimental_repo.library_changed.connect(self.check_if_both_automated_are_disabled)

        self.automated_groups = QButtonGroup()
        self.automated_groups.setExclusive(False)
        self.daily_repo.add_downloads_to_group(self.automated_groups)
        self.experimental_repo.add_downloads_to_group(self.automated_groups)

        self.repos = [
            self.stable_repo,
            self.daily_repo,
            self.experimental_repo,
            self.bforartists_repo,
        ]

        for widget in self.repos:
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)  # type: ignore
            self.addItem(item)
            self.setItemWidget(item, widget)

    @pyqtSlot()
    def check_if_both_automated_are_disabled(self):
        if (not self.daily_repo.library) and (not self.experimental_repo.library) and self.daily_repo.download:
            self.daily_repo.download = False # Will also set experimental_repo
            self.daily_repo.download_enable_button.setEnabled(False)
            self.experimental_repo.download_enable_button.setEnabled(False)
        if (self.daily_repo.library or self.experimental_repo) and not self.daily_repo.download:
            self.daily_repo.download_enable_button.setEnabled(True)
            self.experimental_repo.download_enable_button.setEnabled(True)

    def total_height(self):
        return sum(r.height() for r in self.repos)
