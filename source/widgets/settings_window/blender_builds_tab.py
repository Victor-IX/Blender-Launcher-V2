from __future__ import annotations

from typing import TYPE_CHECKING

from i18n import t
from modules.bl_api_manager import dropdown_blender_version
from modules.platform_utils import get_platform
from modules.settings import (
    favorite_pages,
    get_bash_arguments,
    get_bfa_update_behavior,
    get_blender_startup_arguments,
    get_check_for_new_builds_automatically,
    get_check_for_new_builds_on_startup,
    get_daily_update_behavior,
    get_enable_quick_launch_key_seq,
    get_experimental_update_behavior,
    get_install_template,
    get_launch_blender_no_console,
    get_mark_as_favorite,
    get_minimum_blender_stable_version,
    get_new_builds_check_frequency,
    get_quick_launch_key_seq,
    get_show_bfa_update_button,
    get_show_daily_archive_builds,
    get_show_daily_update_button,
    get_show_experimental_archive_builds,
    get_show_experimental_update_button,
    get_show_patch_archive_builds,
    get_show_stable_update_button,
    get_show_upbge_stable_update_button,
    get_show_upbge_weekly_update_button,
    get_show_update_button,
    get_stable_update_behavior,
    get_upbge_stable_update_behavior,
    get_upbge_weekly_update_behavior,
    get_update_behavior,
    get_use_advanced_update_button,
    set_bash_arguments,
    set_bfa_update_behavior,
    set_blender_startup_arguments,
    set_check_for_new_builds_automatically,
    set_check_for_new_builds_on_startup,
    set_daily_update_behavior,
    set_enable_quick_launch_key_seq,
    set_experimental_update_behavior,
    set_install_template,
    set_launch_blender_no_console,
    set_mark_as_favorite,
    set_minimum_blender_stable_version,
    set_new_builds_check_frequency,
    set_quick_launch_key_seq,
    set_scrape_bfa_builds,
    set_scrape_daily_builds,
    set_scrape_experimental_builds,
    set_scrape_stable_builds,
    set_scrape_upbge_builds,
    set_scrape_upbge_weekly_builds,
    set_show_bfa_builds,
    set_show_bfa_update_button,
    set_show_daily_archive_builds,
    set_show_daily_builds,
    set_show_daily_update_button,
    set_show_experimental_and_patch_builds,
    set_show_experimental_archive_builds,
    set_show_experimental_update_button,
    set_show_patch_archive_builds,
    set_show_stable_builds,
    set_show_stable_update_button,
    set_show_upbge_builds,
    set_show_upbge_stable_update_button,
    set_show_upbge_weekly_builds,
    set_show_upbge_weekly_update_button,
    set_show_update_button,
    set_stable_update_behavior,
    set_upbge_stable_update_behavior,
    set_upbge_weekly_update_behavior,
    set_update_behavior,
    set_use_advanced_update_button,
    update_behavior,
)
from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from widgets.repo_group import RepoGroup
from widgets.settings_form_widget import SettingsFormWidget
from widgets.settings_window.settings_group import SettingsGroup

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class BlenderBuildsTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Repo visibility and downloading settings
        self.repo_settings = SettingsGroup(t("settings.blender_builds.visibility_and_downloading"), parent=self)

        self.repo_group = RepoGroup(self)
        self.repo_group.stable_repo.library_changed.connect(set_show_stable_builds)
        self.repo_group.stable_repo.download_changed.connect(set_scrape_stable_builds)
        self.repo_group.daily_repo.library_changed.connect(set_show_daily_builds)
        self.repo_group.daily_repo.download_changed.connect(set_scrape_daily_builds)
        self.repo_group.experimental_repo.library_changed.connect(set_show_experimental_and_patch_builds)
        self.repo_group.experimental_repo.download_changed.connect(set_scrape_experimental_builds)
        self.repo_group.bforartists_repo.library_changed.connect(set_show_bfa_builds)
        self.repo_group.bforartists_repo.download_changed.connect(set_scrape_bfa_builds)
        self.repo_group.upbge_repo.library_changed.connect(set_show_upbge_builds)
        self.repo_group.upbge_repo.download_changed.connect(set_scrape_upbge_builds)
        self.repo_group.upbge_weekly_repo.library_changed.connect(set_show_upbge_weekly_builds)
        self.repo_group.upbge_weekly_repo.download_changed.connect(set_scrape_upbge_weekly_builds)

        qvl = QVBoxLayout()
        # qvl.setContentsMargins(0, 0, 0, 0)
        qvl.addWidget(self.repo_group)
        self.repo_settings.setLayout(qvl)

        # Checking for builds settings
        self.buildcheck_settings = SettingsGroup(t("settings.blender_builds.checking_for_builds"), parent=self)

        # Minimum stable blender download version (this is mainly for cleanliness and speed)
        self.MinStableBlenderVer = QComboBox()
        # TODO: Add a "custom" key with a new section for custom min version input (useful if you want to fetch very old versions)
        keys = list(dropdown_blender_version().keys())
        self.MinStableBlenderVer.addItems(keys)
        self.MinStableBlenderVer.setToolTip(t("settings.blender_builds.minimum_stable_blender_version_tooltip"))
        self.MinStableBlenderVer.setCurrentText(get_minimum_blender_stable_version())
        self.MinStableBlenderVer.activated[int].connect(self.change_minimum_blender_stable_version)

        # Whether to check for new builds based on a timer
        self.CheckForNewBuildsAutomatically = QCheckBox()
        self.CheckForNewBuildsAutomatically.setChecked(get_check_for_new_builds_automatically())
        self.CheckForNewBuildsAutomatically.setEnabled(True)
        self.CheckForNewBuildsAutomatically.clicked.connect(self.toggle_check_for_new_builds_automatically)
        self.CheckForNewBuildsAutomatically.setText(t("settings.blender_builds.check_automatically"))
        self.CheckForNewBuildsAutomatically.setToolTip(t("settings.blender_builds.check_automatically_tooltip"))

        self.NewBuildsCheckFrequency = QSpinBox()
        self.NewBuildsCheckFrequency.setEnabled(get_check_for_new_builds_automatically())
        self.NewBuildsCheckFrequency.setContextMenuPolicy(Qt.NoContextMenu)
        self.NewBuildsCheckFrequency.setToolTip(t("settings.blender_builds.new_builds_check_frequency_tooltip"))
        self.NewBuildsCheckFrequency.setMaximum(24 * 7 * 4)  # 4 weeks?
        self.NewBuildsCheckFrequency.setMinimum(6)  # Set minimum to 6h
        self.NewBuildsCheckFrequency.setPrefix(t("settings.blender_builds.interval_prefix"))
        self.NewBuildsCheckFrequency.setSuffix("h")
        self.NewBuildsCheckFrequency.setValue(get_new_builds_check_frequency())
        self.NewBuildsCheckFrequency.editingFinished.connect(self.new_builds_check_frequency_changed)

        # Whether to check on startup
        self.CheckForNewBuildsOnStartup = QCheckBox()
        self.CheckForNewBuildsOnStartup.setChecked(get_check_for_new_builds_on_startup())
        self.CheckForNewBuildsOnStartup.clicked.connect(self.toggle_check_on_startup)
        self.CheckForNewBuildsOnStartup.setText(t("settings.blender_builds.on_startup"))
        self.CheckForNewBuildsOnStartup.setToolTip(t("settings.blender_builds.on_startup_tooltip"))

        # Show Archive Builds
        self.show_daily_archive_builds = QCheckBox(self)
        self.show_daily_archive_builds.setText(t("settings.blender_builds.show_daily_archive_builds"))
        self.show_daily_archive_builds.setToolTip(t("settings.blender_builds.show_daily_archive_builds_tooltip"))
        self.show_daily_archive_builds.setChecked(get_show_daily_archive_builds())
        self.show_daily_archive_builds.clicked.connect(self.toggle_show_daily_archive_builds)
        self.show_experimental_archive_builds = QCheckBox(self)
        self.show_experimental_archive_builds.setText(t("settings.blender_builds.show_experimental_archive_builds"))
        self.show_experimental_archive_builds.setToolTip(
            t("settings.blender_builds.show_experimental_archive_builds_tooltip")
        )
        self.show_experimental_archive_builds.setChecked(get_show_experimental_archive_builds())
        self.show_experimental_archive_builds.clicked.connect(self.toggle_show_experimental_archive_builds)
        self.show_patch_archive_builds = QCheckBox(self)
        self.show_patch_archive_builds.setText(t("settings.blender_builds.show_patch_archive_builds"))
        self.show_patch_archive_builds.setToolTip(t("settings.blender_builds.show_patch_archive_builds_tooltip"))
        self.show_patch_archive_builds.setChecked(get_show_patch_archive_builds())
        self.show_patch_archive_builds.clicked.connect(self.toggle_show_patch_archive_builds)

        # Layout
        self.scraping_builds_layout = QGridLayout()
        self.scraping_builds_layout.addWidget(self.CheckForNewBuildsAutomatically, 0, 0, 1, 1)
        self.scraping_builds_layout.addWidget(self.NewBuildsCheckFrequency, 0, 1, 1, 1)
        self.scraping_builds_layout.addWidget(self.CheckForNewBuildsOnStartup, 1, 0, 1, 2)
        self.scraping_builds_layout.addWidget(
            QLabel(t("settings.blender_builds.minimum_stable_build_to_scrape"), self), 2, 0, 1, 1
        )
        self.scraping_builds_layout.addWidget(self.MinStableBlenderVer, 2, 1, 1, 1)
        self.scraping_builds_layout.addWidget(self.show_daily_archive_builds, 3, 0, 1, 2)
        self.scraping_builds_layout.addWidget(self.show_experimental_archive_builds, 4, 0, 1, 2)
        self.scraping_builds_layout.addWidget(self.show_patch_archive_builds, 5, 0, 1, 2)
        self.buildcheck_settings.setLayout(self.scraping_builds_layout)

        # Downloading builds settings
        self.download_settings = SettingsGroup(t("settings.blender_builds.downloading_and_saving_builds"), parent=self)

        # Update button
        self.ShowUpdateButton = QCheckBox()
        self.ShowUpdateButton.setText(t("settings.blender_builds.show_update_button"))
        self.ShowUpdateButton.clicked.connect(self.show_update_button)
        self.ShowUpdateButton.setChecked(get_show_update_button())

        self.UpdateBehavior = QComboBox()
        self.UpdateBehavior.addItems(list(update_behavior.keys()))
        self.UpdateBehavior.setToolTip(t("settings.blender_builds.update_behavior_tooltip"))
        self.UpdateBehavior.setCurrentIndex(get_update_behavior())
        self.UpdateBehavior.activated[int].connect(self.change_update_behavior)
        self.UpdateBehavior.setEnabled(self.ShowUpdateButton.isChecked())

        self.UseAdvancedUpdateButton = QCheckBox()
        self.UseAdvancedUpdateButton.setText(t("settings.blender_builds.use_advanced_update_button"))
        self.UseAdvancedUpdateButton.setToolTip(t("settings.blender_builds.use_advanced_update_button_tooltip"))
        self.UseAdvancedUpdateButton.clicked.connect(self.use_advanced_update_button)
        self.UseAdvancedUpdateButton.setChecked(get_use_advanced_update_button())

        self.show_update_button_tooltip_normal = t("settings.blender_builds.show_update_button_tooltip_normal")
        self.show_update_button_tooltip_disabled = t("settings.blender_builds.show_update_button_tooltip_disabled")

        self.ShowStableUpdateButton = QCheckBox()
        self.ShowStableUpdateButton.setText(t("settings.blender_builds.show_stable_update_button"))
        self.ShowStableUpdateButton.setToolTip(t("settings.blender_builds.show_stable_update_button_tooltip"))
        self.ShowStableUpdateButton.clicked.connect(self.show_stable_update_button)
        self.ShowStableUpdateButton.setChecked(get_show_stable_update_button())

        self.UpdateStableBehavior = QComboBox()
        self.UpdateStableBehavior.addItems(list(update_behavior.keys()))
        self.UpdateStableBehavior.setToolTip(t("settings.blender_builds.update_stable_behavior_tooltip"))
        self.UpdateStableBehavior.setCurrentIndex(get_stable_update_behavior())
        self.UpdateStableBehavior.activated[int].connect(self.change_update_stable_behavior)
        self.UpdateStableBehavior.setEnabled(self.ShowStableUpdateButton.isChecked())

        self.ShowDailyUpdateButton = QCheckBox()
        self.ShowDailyUpdateButton.setText(t("settings.blender_builds.show_daily_update_button"))
        self.ShowDailyUpdateButton.setToolTip(t("settings.blender_builds.show_daily_update_button_tooltip"))
        self.ShowDailyUpdateButton.clicked.connect(self.show_daily_update_button)
        self.ShowDailyUpdateButton.setChecked(get_show_daily_update_button())

        self.UpdateDailyBehavior = QComboBox()
        self.UpdateDailyBehavior.addItems(list(update_behavior.keys()))
        self.UpdateDailyBehavior.setToolTip(t("settings.blender_builds.update_daily_behavior_tooltip"))
        self.UpdateDailyBehavior.setCurrentIndex(get_daily_update_behavior())
        self.UpdateDailyBehavior.activated[int].connect(self.change_update_daily_behavior)
        self.UpdateDailyBehavior.setEnabled(self.ShowDailyUpdateButton.isChecked())

        self.ShowExperimentalUpdateButton = QCheckBox()
        self.ShowExperimentalUpdateButton.setText(t("settings.blender_builds.show_experimental_update_button"))
        self.ShowExperimentalUpdateButton.setToolTip(
            t("settings.blender_builds.show_experimental_update_button_tooltip")
        )
        self.ShowExperimentalUpdateButton.clicked.connect(self.show_experimental_update_button)
        self.ShowExperimentalUpdateButton.setChecked(get_show_experimental_update_button())

        self.UpdateExperimentalBehavior = QComboBox()
        self.UpdateExperimentalBehavior.addItems(list(update_behavior.keys()))
        self.UpdateExperimentalBehavior.setToolTip(t("settings.blender_builds.update_experimental_behavior_tooltip"))
        self.UpdateExperimentalBehavior.setCurrentIndex(get_experimental_update_behavior())
        self.UpdateExperimentalBehavior.activated[int].connect(self.change_update_experimental_behavior)
        self.UpdateExperimentalBehavior.setEnabled(self.ShowExperimentalUpdateButton.isChecked())

        self.ShowBFAUpdateButton = QCheckBox()
        self.ShowBFAUpdateButton.setText(t("settings.blender_builds.show_bfa_update_button"))
        self.ShowBFAUpdateButton.setToolTip(t("settings.blender_builds.show_bfa_update_button_tooltip"))
        self.ShowBFAUpdateButton.clicked.connect(self.show_bfa_update_button)
        self.ShowBFAUpdateButton.setChecked(get_show_bfa_update_button())

        self.UpdateBFABehavior = QComboBox()
        self.UpdateBFABehavior.addItems(list(update_behavior.keys()))
        self.UpdateBFABehavior.setToolTip(t("settings.blender_builds.update_bfa_behavior_tooltip"))
        self.UpdateBFABehavior.setCurrentIndex(get_bfa_update_behavior())
        self.UpdateBFABehavior.activated[int].connect(self.change_update_bfa_behavior)
        self.UpdateBFABehavior.setEnabled(self.ShowBFAUpdateButton.isChecked())

        self.ShowUPBGEStableUpdateButton = QCheckBox()
        self.ShowUPBGEStableUpdateButton.setText(t("settings.blender_builds.show_upbge_stable_update_button"))
        self.ShowUPBGEStableUpdateButton.setToolTip(
            t("settings.blender_builds.show_upbge_stable_update_button_tooltip")
        )
        self.ShowUPBGEStableUpdateButton.clicked.connect(self.show_upbge_stable_update_button)
        self.ShowUPBGEStableUpdateButton.setChecked(get_show_upbge_stable_update_button())

        self.UpdateUPBGEStableBehavior = QComboBox()
        self.UpdateUPBGEStableBehavior.addItems(list(update_behavior.keys()))
        self.UpdateUPBGEStableBehavior.setToolTip(t("settings.blender_builds.update_upbge_stable_behavior_tooltip"))
        self.UpdateUPBGEStableBehavior.setCurrentIndex(get_upbge_stable_update_behavior())
        self.UpdateUPBGEStableBehavior.activated[int].connect(self.change_update_upbge_stable_behavior)
        self.UpdateUPBGEStableBehavior.setEnabled(self.ShowUPBGEStableUpdateButton.isChecked())

        self.ShowUPBGEWeeklyUpdateButton = QCheckBox()
        self.ShowUPBGEWeeklyUpdateButton.setText(t("settings.blender_builds.show_upbge_weekly_update_button"))
        self.ShowUPBGEWeeklyUpdateButton.setToolTip(
            t("settings.blender_builds.show_upbge_weekly_update_button_tooltip")
        )
        self.ShowUPBGEWeeklyUpdateButton.clicked.connect(self.show_upbge_weekly_update_button)
        self.ShowUPBGEWeeklyUpdateButton.setChecked(get_show_upbge_weekly_update_button())

        self.UpdateUPBGEWeeklyBehavior = QComboBox()
        self.UpdateUPBGEWeeklyBehavior.addItems(list(update_behavior.keys()))
        self.UpdateUPBGEWeeklyBehavior.setToolTip(t("settings.blender_builds.update_upbge_weekly_behavior_tooltip"))
        self.UpdateUPBGEWeeklyBehavior.setCurrentIndex(get_upbge_weekly_update_behavior())
        self.UpdateUPBGEWeeklyBehavior.activated[int].connect(self.change_update_upbge_weekly_behavior)
        self.UpdateUPBGEWeeklyBehavior.setEnabled(self.ShowUPBGEWeeklyUpdateButton.isChecked())

        # Mark As Favorite
        self.EnableMarkAsFavorite = QCheckBox()
        self.EnableMarkAsFavorite.setText(t("settings.blender_builds.mark_as_favorite"))
        self.EnableMarkAsFavorite.setToolTip(t("settings.blender_builds.mark_as_favorite_tooltip"))
        self.EnableMarkAsFavorite.setChecked(get_mark_as_favorite() != 0)
        self.EnableMarkAsFavorite.clicked.connect(self.toggle_mark_as_favorite)
        self.MarkAsFavorite = QComboBox()
        self.MarkAsFavorite.addItems([fav for fav in favorite_pages if fav != "Disable"])
        self.MarkAsFavorite.setToolTip(t("settings.blender_builds.select_favorite_tab_tooltip"))
        self.MarkAsFavorite.setCurrentIndex(max(get_mark_as_favorite() - 1, 0))
        self.MarkAsFavorite.activated[int].connect(self.change_mark_as_favorite)
        self.MarkAsFavorite.setEnabled(self.EnableMarkAsFavorite.isChecked())

        # Install Template
        self.InstallTemplate = QCheckBox()
        self.InstallTemplate.setText(t("settings.blender_builds.install_template"))
        self.InstallTemplate.setToolTip(t("settings.blender_builds.install_template_tooltip"))
        self.InstallTemplate.clicked.connect(self.toggle_install_template)
        self.InstallTemplate.setChecked(get_install_template())

        self.advanced_settings_widget = QWidget()
        self.advanced_settings_layout = QGridLayout(self.advanced_settings_widget)
        self.advanced_settings_layout.setContentsMargins(0, 0, 0, 0)

        # Advanced settings layout
        self.advanced_settings_layout.addWidget(self.ShowStableUpdateButton, 0, 0, 1, 1)
        self.advanced_settings_layout.addWidget(self.UpdateStableBehavior, 0, 1, 1, 2)
        self.advanced_settings_layout.addWidget(self.ShowDailyUpdateButton, 1, 0, 1, 1)
        self.advanced_settings_layout.addWidget(self.UpdateDailyBehavior, 1, 1, 1, 2)
        self.advanced_settings_layout.addWidget(self.ShowExperimentalUpdateButton, 2, 0, 1, 1)
        self.advanced_settings_layout.addWidget(self.UpdateExperimentalBehavior, 2, 1, 1, 2)
        self.advanced_settings_layout.addWidget(self.ShowBFAUpdateButton, 3, 0, 1, 1)
        self.advanced_settings_layout.addWidget(self.UpdateBFABehavior, 3, 1, 1, 2)
        self.advanced_settings_layout.addWidget(self.ShowUPBGEStableUpdateButton, 4, 0, 1, 1)
        self.advanced_settings_layout.addWidget(self.UpdateUPBGEStableBehavior, 4, 1, 1, 2)
        self.advanced_settings_layout.addWidget(self.ShowUPBGEWeeklyUpdateButton, 5, 0, 1, 1)
        self.advanced_settings_layout.addWidget(self.UpdateUPBGEWeeklyBehavior, 5, 1, 1, 2)

        is_advanced = get_use_advanced_update_button()
        self.advanced_settings_widget.setVisible(is_advanced)

        self.ShowUpdateButton.setEnabled(not is_advanced)
        self.UpdateBehavior.setEnabled(not is_advanced and self.ShowUpdateButton.isChecked())

        if is_advanced:
            self.ShowUpdateButton.setToolTip(t("settings.blender_builds.show_update_button_tooltip_disabled"))
        else:
            self.ShowUpdateButton.setToolTip(t("settings.blender_builds.show_update_button_tooltip_normal"))

        self.downloading_layout = QGridLayout()
        self.downloading_layout.addWidget(self.ShowUpdateButton, 0, 0, 1, 1)
        self.downloading_layout.addWidget(self.UpdateBehavior, 0, 1, 1, 2)
        self.downloading_layout.addWidget(self.UseAdvancedUpdateButton, 1, 0, 1, 3)
        self.downloading_layout.addWidget(self.advanced_settings_widget, 2, 0, 1, 3)
        self.downloading_layout.addWidget(self.EnableMarkAsFavorite, 3, 0, 1, 1)
        self.downloading_layout.addWidget(self.MarkAsFavorite, 3, 1, 1, 2)
        self.downloading_layout.addWidget(self.InstallTemplate, 4, 0, 1, 3)
        self.download_settings.setLayout(self.downloading_layout)

        # Launching builds settings
        self.launching_settings = SettingsGroup(t("settings.blender_builds.launching_builds"), parent=self)

        # Quick Launch Key Sequence
        self.EnableQuickLaunchKeySeq = QCheckBox()
        self.EnableQuickLaunchKeySeq.setText(t("settings.blender_builds.quick_launch_global_shortcut"))
        self.EnableQuickLaunchKeySeq.setToolTip(t("settings.blender_builds.quick_launch_global_shortcut_tooltip"))
        self.EnableQuickLaunchKeySeq.clicked.connect(self.toggle_enable_quick_launch_key_seq)
        self.EnableQuickLaunchKeySeq.setChecked(get_enable_quick_launch_key_seq())
        self.QuickLaunchKeySeq = QLineEdit()
        self.QuickLaunchKeySeq.setEnabled(get_enable_quick_launch_key_seq())
        self.QuickLaunchKeySeq.keyPressEvent = self._keyPressEvent
        self.QuickLaunchKeySeq.setText(str(get_quick_launch_key_seq()))
        self.QuickLaunchKeySeq.setToolTip(t("settings.blender_builds.quick_launch_key_seq_tooltip"))
        self.QuickLaunchKeySeq.setContextMenuPolicy(Qt.NoContextMenu)
        self.QuickLaunchKeySeq.setCursorPosition(0)
        self.QuickLaunchKeySeq.editingFinished.connect(self.update_quick_launch_key_seq)
        # Run Blender using blender-launcher.exe
        self.LaunchBlenderNoConsole = QCheckBox()
        self.LaunchBlenderNoConsole.setText(t("settings.blender_builds.hide_console_on_startup"))
        self.LaunchBlenderNoConsole.setToolTip(t("settings.blender_builds.hide_console_on_startup_tooltip"))
        self.LaunchBlenderNoConsole.clicked.connect(self.toggle_launch_blender_no_console)
        self.LaunchBlenderNoConsole.setChecked(get_launch_blender_no_console())
        # Blender Startup Arguments
        self.BlenderStartupArguments = QLineEdit()
        self.BlenderStartupArguments.setText(str(get_blender_startup_arguments()))
        self.BlenderStartupArguments.setToolTip(t("settings.blender_builds.blender_startup_arguments_tooltip"))
        self.BlenderStartupArguments.setContextMenuPolicy(Qt.NoContextMenu)
        self.BlenderStartupArguments.setCursorPosition(0)
        self.BlenderStartupArguments.editingFinished.connect(self.update_blender_startup_arguments)
        # Command Line Arguments
        self.BashArguments = QLineEdit()
        self.BashArguments.setText(str(get_bash_arguments()))
        self.BashArguments.setToolTip(t("settings.blender_builds.bash_arguments_tooltip"))
        self.BashArguments.setContextMenuPolicy(Qt.NoContextMenu)
        self.BashArguments.setCursorPosition(0)
        self.BashArguments.editingFinished.connect(self.update_bash_arguments)

        self.launching_layout = QFormLayout()
        self.launching_layout.addRow(self.EnableQuickLaunchKeySeq, self.QuickLaunchKeySeq)
        if get_platform() == "Windows":
            self.launching_layout.addRow(self.LaunchBlenderNoConsole)
        if get_platform() == "Linux":
            self.launching_layout.addRow(QLabel(t("settings.blender_builds.bash_arguments"), self))
            self.launching_layout.addRow(self.BashArguments)
            self.launching_layout.addRow(QLabel(t("settings.blender_builds.startup_arguments"), self))
            self.launching_layout.addRow(self.BlenderStartupArguments)

        self.launching_settings.setLayout(self.launching_layout)

        # Layout
        self.addRow(self.repo_settings)
        self.addRow(self.buildcheck_settings)
        self.addRow(self.download_settings)
        self.addRow(self.launching_settings)

    def change_mark_as_favorite(self, index: int):
        page = self.MarkAsFavorite.itemText(index)
        set_mark_as_favorite(page)

    def change_minimum_blender_stable_version(self, index: int):
        minimum = self.MinStableBlenderVer.itemText(index)
        set_minimum_blender_stable_version(minimum)

    def update_blender_startup_arguments(self):
        args = self.BlenderStartupArguments.text()
        set_blender_startup_arguments(args)

    def update_bash_arguments(self):
        args = self.BashArguments.text()
        set_bash_arguments(args)

    def show_update_button(self, is_checked):
        self.UpdateBehavior.setEnabled(is_checked)
        set_show_update_button(is_checked)

    def use_advanced_update_button(self, is_checked):
        self.advanced_settings_widget.setVisible(is_checked)

        self.ShowUpdateButton.setEnabled(not is_checked)
        self.UpdateBehavior.setEnabled(not is_checked and self.ShowUpdateButton.isChecked())

        if is_checked:
            self.ShowUpdateButton.setToolTip(self.show_update_button_tooltip_disabled)
        else:
            self.ShowUpdateButton.setToolTip(self.show_update_button_tooltip_normal)

        set_use_advanced_update_button(is_checked)

    def show_stable_update_button(self, is_checked):
        self.UpdateStableBehavior.setEnabled(is_checked)
        set_show_stable_update_button(is_checked)

    def show_daily_update_button(self, is_checked):
        self.UpdateDailyBehavior.setEnabled(is_checked)
        set_show_daily_update_button(is_checked)

    def show_experimental_update_button(self, is_checked):
        self.UpdateExperimentalBehavior.setEnabled(is_checked)
        set_show_experimental_update_button(is_checked)

    def show_bfa_update_button(self, is_checked):
        self.UpdateBFABehavior.setEnabled(is_checked)
        set_show_bfa_update_button(is_checked)

    def show_upbge_stable_update_button(self, is_checked):
        self.UpdateUPBGEStableBehavior.setEnabled(is_checked)
        set_show_upbge_stable_update_button(is_checked)

    def show_upbge_weekly_update_button(self, is_checked):
        self.UpdateUPBGEWeeklyBehavior.setEnabled(is_checked)
        set_show_upbge_weekly_update_button(is_checked)

    def change_update_behavior(self, index: int):
        behavior = self.UpdateBehavior.itemText(index)
        set_update_behavior(behavior)

    def change_update_stable_behavior(self, index: int):
        behavior = self.UpdateStableBehavior.itemText(index)
        set_stable_update_behavior(behavior)

    def change_update_daily_behavior(self, index: int):
        behavior = self.UpdateDailyBehavior.itemText(index)
        set_daily_update_behavior(behavior)

    def change_update_experimental_behavior(self, index: int):
        behavior = self.UpdateExperimentalBehavior.itemText(index)
        set_experimental_update_behavior(behavior)

    def change_update_bfa_behavior(self, index: int):
        behavior = self.UpdateBFABehavior.itemText(index)
        set_bfa_update_behavior(behavior)

    def change_update_upbge_stable_behavior(self, index: int):
        behavior = self.UpdateUPBGEStableBehavior.itemText(index)
        set_upbge_stable_update_behavior(behavior)

    def change_update_upbge_weekly_behavior(self, index: int):
        behavior = self.UpdateUPBGEWeeklyBehavior.itemText(index)
        set_upbge_weekly_update_behavior(behavior)

    def toggle_install_template(self, is_checked):
        set_install_template(is_checked)

    def toggle_mark_as_favorite(self, is_checked):
        self.MarkAsFavorite.setEnabled(is_checked)
        if is_checked:
            set_mark_as_favorite(self.MarkAsFavorite.currentText())
        else:
            set_mark_as_favorite("Disable")

    def toggle_launch_blender_no_console(self, is_checked):
        set_launch_blender_no_console(is_checked)

    def update_quick_launch_key_seq(self):
        key_seq = self.QuickLaunchKeySeq.text()
        set_quick_launch_key_seq(key_seq)

    def toggle_enable_quick_launch_key_seq(self, is_checked):
        set_enable_quick_launch_key_seq(is_checked)
        self.QuickLaunchKeySeq.setEnabled(is_checked)

    def _keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        key_name = ""
        key = e.key()
        modifiers = e.modifiers()

        modifier_strings = []

        if modifiers & Qt.ControlModifier:
            modifier_strings.append("Ctrl")
        if modifiers & Qt.AltModifier:
            modifier_strings.append("Alt")
        if modifiers & Qt.ShiftModifier:
            modifier_strings.append("Shift")
        # TODO: Check if it's possible to use the Meta key
        # if modifiers & Qt.MetaModifier:
        #     modifier_strings.append("Meta")

        modifier_str = "+".join(modifier_strings)

        if key > 0 and key not in {Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta}:
            key_str = QtGui.QKeySequence(key).toString()
            if modifier_str:
                key_name = f"{modifier_str}+{key_str}"
            else:
                key_name = key_str

        if key_name != "":
            # Remap <Shift + *> keys sequences
            if "Shift" in key_name:
                alt_chars = '~!@#$%^&*()_+|{}:"<>?'
                real_chars = r"`1234567890-=\[];',./"
                trans_table = str.maketrans(alt_chars, real_chars)
                trans = key_name[-1].translate(trans_table)
                key_name = key_name[:-1] + trans

            self.QuickLaunchKeySeq.setText(key_name.lower())

        return super().keyPressEvent(e)

    def toggle_check_for_new_builds_automatically(self, is_checked):
        set_check_for_new_builds_automatically(is_checked)
        self.NewBuildsCheckFrequency.setEnabled(is_checked)

    def new_builds_check_frequency_changed(self):
        set_new_builds_check_frequency(self.NewBuildsCheckFrequency.value())

    def toggle_check_on_startup(self, is_checked):
        set_check_for_new_builds_on_startup(is_checked)
        self.CheckForNewBuildsOnStartup.setChecked(is_checked)

    def toggle_scrape_stable_builds(self, is_checked):
        set_scrape_stable_builds(is_checked)

    def toggle_scrape_daily_builds(self, is_checked):
        set_scrape_daily_builds(is_checked)

    def toggle_scrape_experimental_builds(self, is_checked):
        set_scrape_experimental_builds(is_checked)

    def toggle_scrape_bfa_builds(self, is_checked):
        set_scrape_bfa_builds(is_checked)

    def toggle_scrape_upbge_builds(self, is_checked):
        set_scrape_upbge_builds(is_checked)

    def toggle_scrape_upbge_weekly_builds(self, is_checked):
        set_scrape_upbge_weekly_builds(is_checked)

    def toggle_show_daily_archive_builds(self, is_checked):
        set_show_daily_archive_builds(is_checked)
        self.show_daily_archive_builds.setChecked(is_checked)

    def toggle_show_experimental_archive_builds(self, is_checked):
        set_show_experimental_archive_builds(is_checked)
        self.show_experimental_archive_builds.setChecked(is_checked)

    def toggle_show_patch_archive_builds(self, is_checked):
        set_show_patch_archive_builds(is_checked)
        self.show_patch_archive_builds.setChecked(is_checked)
