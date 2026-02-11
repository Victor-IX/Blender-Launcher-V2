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
    QComboBox,
    QLineEdit,
)
from widgets.repo_group import RepoGroup
from widgets.settings_form_widget import SettingsFormWidget

if TYPE_CHECKING:
    from windows.main_window import BlenderLauncher


class BlenderBuildsTabWidget(SettingsFormWidget):
    def __init__(self, parent: BlenderLauncher):
        super().__init__(parent=parent)
        self.launcher: BlenderLauncher = parent

        # Repo visibility and downloading settings
        with self.group("settings.blender_builds.visibility_and_downloading") as grp:
            self.repo_group = grp.add(RepoGroup(self))
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

        # Checking for builds settings
        with self.group("settings.blender_builds.checking_for_builds") as grp:
            # Minimum stable blender download version (this is mainly for cleanliness and speed)
            self.MinStableBlenderVer = grp.add(QComboBox(), "settings.blender_builds.minimum_stable_build_to_scrape")
            # TODO: Add a "custom" key with a new section for custom min version input (useful if you want to fetch very old versions)
            keys = list(dropdown_blender_version().keys())
            self.MinStableBlenderVer.addItems(keys)
            self.MinStableBlenderVer.setToolTip(t("settings.blender_builds.minimum_stable_blender_version_tooltip"))
            self.MinStableBlenderVer.setCurrentText(get_minimum_blender_stable_version())
            self.MinStableBlenderVer.activated[int].connect(self.change_minimum_blender_stable_version)

            # Whether to check for new builds based on a timer
            with grp.checked_hgroup(
                "settings.blender_builds.check_automatically",
                default=get_check_for_new_builds_automatically(),
                setter=set_check_for_new_builds_automatically,
            ) as check_group:
                NewBuildsCheckFrequency = check_group.add_spin(
                    None,
                    default=get_new_builds_check_frequency(),
                    setter=set_new_builds_check_frequency,
                    min_=6,  # 6h
                    max_=24 * 7 * 4,  # 4 weeks??
                )
                # NewBuildsCheckFrequency.setPrefix(t("settings.blender_builds.interval_prefix"))
                NewBuildsCheckFrequency.setSuffix("h")

            # Whether to check on startup
            grp.add_checkbox(
                "settings.blender_builds.on_startup",
                default=get_check_for_new_builds_on_startup(),
                setter=set_check_for_new_builds_on_startup,
            )

            # Show Archive Builds
            grp.add_checkbox(
                "settings.blender_builds.show_daily_archive_builds",
                default=get_show_daily_archive_builds(),
                setter=set_show_daily_archive_builds,
            )
            grp.add_checkbox(
                "settings.blender_builds.show_experimental_archive_builds",
                default=get_show_experimental_archive_builds(),
                setter=set_show_experimental_archive_builds,
            )
            grp.add_checkbox(
                "settings.blender_builds.show_patch_archive_builds",
                default=get_show_patch_archive_builds(),
                setter=set_show_patch_archive_builds,
            )

        self.show_update_button_tooltip_normal = t("settings.blender_builds.show_update_button_tooltip_normal")
        self.show_update_button_tooltip_disabled = t("settings.blender_builds.show_update_button_tooltip_disabled")
        # Downloading builds settings
        with self.group("settings.blender_builds.downloading_and_saving_builds") as grp:
            # Update button
            with grp.checked_hgroup(
                "settings.blender_builds.show_update_button",
                default=get_show_update_button(),
                setter=self.show_update_button,
            ) as update_group:
                self.UpdateBehavior = update_group.add(QComboBox())
                self.UpdateBehavior.addItems(list(update_behavior.keys()))
                self.UpdateBehavior.setToolTip(t("settings.blender_builds.update_behavior_tooltip"))
                self.UpdateBehavior.setCurrentIndex(get_update_behavior())
                self.UpdateBehavior.activated[int].connect(self.change_update_behavior)

            # Advanced Update
            with grp.checked_vgroup(
                "settings.blender_builds.use_advanced_update_button",
                default=get_use_advanced_update_button(),
                setter=set_use_advanced_update_button,
                margin=True,
            ) as advanced:
                with advanced.checked_hgroup(
                    "settings.blender_builds.show_stable_update_button",
                    default=get_show_stable_update_button(),
                    setter=set_show_stable_update_button,
                ) as stable:
                    self.UpdateStableBehavior = stable.add(QComboBox())
                    self.UpdateStableBehavior.addItems(list(update_behavior.keys()))
                    self.UpdateStableBehavior.setToolTip(t("settings.blender_builds.update_stable_behavior_tooltip"))
                    self.UpdateStableBehavior.setCurrentIndex(get_stable_update_behavior())
                    self.UpdateStableBehavior.activated[int].connect(self.change_update_stable_behavior)

                with advanced.checked_hgroup(
                    "settings.blender_builds.show_daily_update_button",
                    default=get_show_daily_update_button(),
                    setter=set_show_daily_update_button,
                ) as daily:
                    self.UpdateDailyBehavior = daily.add(QComboBox())
                    self.UpdateDailyBehavior.addItems(list(update_behavior.keys()))
                    self.UpdateDailyBehavior.setToolTip(t("settings.blender_builds.update_daily_behavior_tooltip"))
                    self.UpdateDailyBehavior.setCurrentIndex(get_daily_update_behavior())
                    self.UpdateDailyBehavior.activated[int].connect(self.change_update_daily_behavior)

                with advanced.checked_hgroup(
                    "settings.blender_builds.show_experimental_update_button",
                    default=get_show_experimental_update_button(),
                    setter=set_show_experimental_update_button,
                ) as exp:
                    self.UpdateExperimentalBehavior = exp.add(QComboBox())
                    self.UpdateExperimentalBehavior.addItems(list(update_behavior.keys()))
                    self.UpdateExperimentalBehavior.setToolTip(
                        t("settings.blender_builds.update_experimental_behavior_tooltip")
                    )
                    self.UpdateExperimentalBehavior.setCurrentIndex(get_experimental_update_behavior())
                    self.UpdateExperimentalBehavior.activated[int].connect(self.change_update_experimental_behavior)

                with advanced.checked_hgroup(
                    "settings.blender_builds.show_bfa_update_button",
                    default=get_show_bfa_update_button(),
                    setter=set_show_bfa_update_button,
                ) as bfa:
                    self.UpdateBFABehavior = bfa.add(QComboBox())
                    self.UpdateBFABehavior.addItems(list(update_behavior.keys()))
                    self.UpdateBFABehavior.setToolTip(t("settings.blender_builds.update_bfa_behavior_tooltip"))
                    self.UpdateBFABehavior.setCurrentIndex(get_bfa_update_behavior())
                    self.UpdateBFABehavior.activated[int].connect(self.change_update_bfa_behavior)

                with advanced.checked_hgroup(
                    "settings.blender_builds.show_upbge_stable_update_button",
                    default=get_show_upbge_stable_update_button(),
                    setter=set_show_upbge_stable_update_button,
                ) as us:
                    self.UpdateUPBGEStableBehavior = us.add(QComboBox())
                    self.UpdateUPBGEStableBehavior.addItems(list(update_behavior.keys()))
                    self.UpdateUPBGEStableBehavior.setToolTip(
                        t("settings.blender_builds.update_upbge_stable_behavior_tooltip")
                    )
                    self.UpdateUPBGEStableBehavior.setCurrentIndex(get_upbge_stable_update_behavior())
                    self.UpdateUPBGEStableBehavior.activated[int].connect(self.change_update_upbge_stable_behavior)

                with advanced.checked_hgroup(
                    "settings.blender_builds.show_upbge_weekly_update_button",
                    default=get_show_upbge_weekly_update_button(),
                    setter=set_show_upbge_weekly_update_button,
                ) as us:
                    self.UpdateUPBGEWeeklyBehavior = us.add(QComboBox())
                    self.UpdateUPBGEWeeklyBehavior.addItems(list(update_behavior.keys()))
                    self.UpdateUPBGEWeeklyBehavior.setToolTip(
                        t("settings.blender_builds.update_upbge_weekly_behavior_tooltip")
                    )
                    self.UpdateUPBGEWeeklyBehavior.setCurrentIndex(get_upbge_weekly_update_behavior())
                    self.UpdateUPBGEWeeklyBehavior.activated[int].connect(self.change_update_upbge_weekly_behavior)

            # Mark As Favorite
            with grp.checked_hgroup(
                "settings.blender_builds.mark_as_favorite",
                default=get_mark_as_favorite() != 0,
                setter=self.toggle_mark_as_favorite,
            ) as fav:
                self.MarkAsFavorite = fav.add(QComboBox())
                self.MarkAsFavorite.addItems([fav for fav in favorite_pages if fav != "Disable"])
                self.MarkAsFavorite.setToolTip(t("settings.blender_builds.select_favorite_tab_tooltip"))
                self.MarkAsFavorite.setCurrentIndex(max(get_mark_as_favorite() - 1, 0))
                self.MarkAsFavorite.activated[int].connect(self.change_mark_as_favorite)

            # Install Template
            grp.add_checkbox(
                "settings.blender_builds.install_template",
                default=get_install_template(),
                setter=set_install_template,
            )

        # Launching builds settings
        with self.group("settings.blender_builds.launching_builds").contents.checked_hgroup(
            "settings.blender_builds.quick_launch_global_shortcut",
            default=get_enable_quick_launch_key_seq(),
            setter=set_enable_quick_launch_key_seq,
        ) as q:
            # Quick Launch Key Sequence
            self.QuickLaunchKeySeq = q.add(QLineEdit())
            self.QuickLaunchKeySeq.keyPressEvent = self._keyPressEvent
            self.QuickLaunchKeySeq.setText(str(get_quick_launch_key_seq()))
            self.QuickLaunchKeySeq.setToolTip(t("settings.blender_builds.quick_launch_key_seq_tooltip"))
            self.QuickLaunchKeySeq.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.QuickLaunchKeySeq.setCursorPosition(0)
            self.QuickLaunchKeySeq.editingFinished.connect(self.update_quick_launch_key_seq)

        # self.launching_settings = SettingsGroup(t("settings.blender_builds.launching_builds"), parent=self)
        with self.group("settings.blender_builds.launching_builds") as grp:
            plat = get_platform()
            if plat == "Windows":
                # Run Blender using blender-launcher.exe
                grp.add_checkbox(
                    "settings.blender_builds.hide_console_on_startup",
                    default=get_launch_blender_no_console(),
                    setter=set_launch_blender_no_console,
                )
            else:
                # Blender Startup Arguments
                grp.add_label("settings.blender_builds.bash_arguments")
                self.BlenderStartupArguments = grp.add(QLineEdit())
                self.BlenderStartupArguments.setText(str(get_blender_startup_arguments()))
                self.BlenderStartupArguments.setToolTip(t("settings.blender_builds.blender_startup_arguments_tooltip"))
                self.BlenderStartupArguments.setContextMenuPolicy(Qt.NoContextMenu)
                self.BlenderStartupArguments.setCursorPosition(0)
                self.BlenderStartupArguments.editingFinished.connect(self.update_blender_startup_arguments)

                # Command Line Arguments
                grp.add_label("settings.blender_builds.startup_arguments")
                self.BashArguments = grp.add(QLineEdit())
                self.BashArguments.setText(str(get_bash_arguments()))
                self.BashArguments.setToolTip(t("settings.blender_builds.bash_arguments_tooltip"))
                self.BashArguments.setContextMenuPolicy(Qt.NoContextMenu)
                self.BashArguments.setCursorPosition(0)
                self.BashArguments.editingFinished.connect(self.update_bash_arguments)

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

    def toggle_mark_as_favorite(self, is_checked):
        if is_checked:
            set_mark_as_favorite(self.MarkAsFavorite.currentText())
        else:
            set_mark_as_favorite("Disable")

    def update_quick_launch_key_seq(self):
        key_seq = self.QuickLaunchKeySeq.text()
        set_quick_launch_key_seq(key_seq)

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
