from i18n import t
from modules.settings import (
    get_scrape_bfa_builds,
    get_scrape_daily_builds,
    get_scrape_experimental_builds,
    get_scrape_stable_builds,
    get_scrape_upbge_builds,
    get_scrape_upbge_weekly_builds,
    get_show_bfa_builds,
    get_show_daily_builds,
    get_show_experimental_and_patch_builds,
    get_show_stable_builds,
    get_show_upbge_builds,
    get_show_upbge_weekly_builds,
)
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout
from widgets.repo_visibility_view import RepoUserView


class RepoGroup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("SettingsGroup", True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

        self.stable_repo = RepoUserView(
            "Stable",
            t("repo.stable_tooltip"),
            library=get_show_stable_builds(),
            download=get_scrape_stable_builds(),
            parent=self,
        )
        self.daily_repo = RepoUserView(
            "Daily",
            t("repo.daily_tooltip"),
            library=get_show_daily_builds(),
            download=get_scrape_daily_builds(),
            parent=self,
        )
        self.experimental_repo = RepoUserView(
            "Experimental and Patch",
            t("repo.experimental_tooltip"),
            library=get_show_experimental_and_patch_builds(),
            download=get_scrape_experimental_builds(),
            parent=self,
        )
        self.bforartists_repo = RepoUserView(
            "Bforartists",
            "A popular fork of Blender with the goal of improving the UI.",
            library=get_show_bfa_builds(),
            download=get_scrape_bfa_builds(),
            parent=self,
        )
        self.upbge_repo = RepoUserView(
            "UPBGE",
            t("repo.upbge_tooltip"),
            library=get_show_upbge_builds(),
            download=get_scrape_upbge_builds(),
            parent=self,
        )
        self.upbge_weekly_repo = RepoUserView(
            "UPBGE Weekly",
            t("repo.upbge_weekly_tooltip"),
            library=get_show_upbge_weekly_builds(),
            download=get_scrape_upbge_weekly_builds(),
            parent=self,
        )

        self.repos = [
            self.stable_repo,
            self.daily_repo,
            self.experimental_repo,
            self.bforartists_repo,
            self.upbge_repo,
            self.upbge_weekly_repo,
        ]

        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 5)

        for widget in self.repos:
            self.layout_.addWidget(widget)

    def total_height(self):
        return sum(r.height() for r in self.repos)
