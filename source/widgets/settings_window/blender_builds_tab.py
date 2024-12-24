from modules._platform import get_platform
from modules.bl_api_manager import dropdown_blender_version
from modules.settings import (
    favorite_pages,
    get_bash_arguments,
    get_blender_startup_arguments,
    get_check_for_new_builds_automatically,
    get_check_for_new_builds_on_startup,
    get_enable_quick_launch_key_seq,
    get_install_template,
    get_launch_blender_no_console,
    get_mark_as_favorite,
    get_minimum_blender_stable_version,
    get_new_builds_check_frequency,
    get_quick_launch_key_seq,
    get_show_daily_archive_builds,
    get_show_experimental_archive_builds,
    get_show_patch_archive_builds,
    set_bash_arguments,
    set_blender_startup_arguments,
    set_check_for_new_builds_automatically,
    set_check_for_new_builds_on_startup,
    set_enable_quick_launch_key_seq,
    set_install_template,
    set_launch_blender_no_console,
    set_mark_as_favorite,
    set_minimum_blender_stable_version,
    set_new_builds_check_frequency,
    set_quick_launch_key_seq,
    set_scrape_automated_builds,
    set_scrape_bfa_builds,
    set_scrape_stable_builds,
    set_show_bfa_builds,
    set_show_daily_archive_builds,
    set_show_daily_builds,
    set_show_experimental_and_patch_builds,
    set_show_experimental_archive_builds,
    set_show_patch_archive_builds,
    set_show_stable_builds,
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
)
from widgets.repo_group import RepoGroup
from widgets.settings_form_widget import SettingsFormWidget
from widgets.settings_window.settings_group import SettingsGroup


class BlenderBuildsTabWidget(SettingsFormWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # Repo visibility and downloading settings
        self.repo_settings = SettingsGroup("Visibility and Downloading", parent=self)

        self.repo_group = RepoGroup(self)
        self.repo_group.stable_repo.library_changed.connect(lambda b: set_show_stable_builds(b))
        self.repo_group.stable_repo.download_changed.connect(self.toggle_scrape_stable_builds)
        self.repo_group.daily_repo.library_changed.connect(lambda b: set_show_daily_builds(b))
        self.repo_group.daily_repo.download_changed.connect(self.toggle_scrape_automated_builds)
        self.repo_group.experimental_repo.library_changed.connect(lambda b: set_show_experimental_and_patch_builds(b))
        self.repo_group.bforartists_repo.library_changed.connect(lambda b: set_show_bfa_builds(b))
        self.repo_group.bforartists_repo.download_changed.connect(self.toggle_scrape_bfa_builds)

        qvl = QVBoxLayout()
        # qvl.setContentsMargins(0, 0, 0, 0)
        qvl.addWidget(self.repo_group)
        self.repo_settings.setLayout(qvl)

        # Checking for builds settings
        self.buildcheck_settings = SettingsGroup("Checking For Builds", parent=self)

        # Minimum stable blender download version (this is mainly for cleanliness and speed)
        self.MinStableBlenderVer = QComboBox()
        # TODO: Add a "custom" key with a new section for custom min version input (useful if you want to fetch very old versions)
        keys = list(dropdown_blender_version().keys())
        self.MinStableBlenderVer.addItems(keys)
        self.MinStableBlenderVer.setToolTip(
            "Minimum stable Blender version to scrape\
            \nDEFAULT: 3.2"
        )
        self.MinStableBlenderVer.setCurrentText(get_minimum_blender_stable_version())
        self.MinStableBlenderVer.activated[int].connect(self.change_minimum_blender_stable_version)

        # Whether to check for new builds based on a timer
        self.CheckForNewBuildsAutomatically = QCheckBox()
        self.CheckForNewBuildsAutomatically.setChecked(False)
        self.CheckForNewBuildsAutomatically.clicked.connect(self.toggle_check_for_new_builds_automatically)
        self.CheckForNewBuildsAutomatically.setText("Check automatically")
        self.CheckForNewBuildsAutomatically.setToolTip(
            "Check for new Blender builds automatically\
            \nDEFAULT: Off"
        )
        # How often to check for new builds if ^^ enabled
        self.NewBuildsCheckFrequency = QSpinBox()
        self.NewBuildsCheckFrequency.setEnabled(get_check_for_new_builds_automatically())
        self.NewBuildsCheckFrequency.setContextMenuPolicy(Qt.NoContextMenu)
        self.NewBuildsCheckFrequency.setToolTip(
            "Time in hours between new Blender builds check\
            \nDEFAULT: 12h"
        )
        self.NewBuildsCheckFrequency.setMaximum(24 * 7 * 4)  # 4 weeks?
        self.NewBuildsCheckFrequency.setMinimum(12)
        self.NewBuildsCheckFrequency.setPrefix("Interval: ")
        self.NewBuildsCheckFrequency.setSuffix("h")
        self.NewBuildsCheckFrequency.setValue(get_new_builds_check_frequency())
        self.NewBuildsCheckFrequency.editingFinished.connect(self.new_builds_check_frequency_changed)
        # Whether to check on startup
        self.CheckForNewBuildsOnStartup = QCheckBox()
        self.CheckForNewBuildsOnStartup.setChecked(get_check_for_new_builds_on_startup())
        self.CheckForNewBuildsOnStartup.clicked.connect(self.toggle_check_on_startup)
        self.CheckForNewBuildsOnStartup.setText("On startup")
        self.CheckForNewBuildsOnStartup.setToolTip(
            "Check for new Blender builds on Blender Launcher startup\
            \nDEFAULT: On"
        )

        # Show Archive Builds
        self.show_daily_archive_builds = QCheckBox(self)
        self.show_daily_archive_builds.setText("Show Daily Archived Builds")
        self.show_daily_archive_builds.setToolTip(
            "Show Daily Archived Builds\
            \nDEFAULT: Off"
        )
        self.show_daily_archive_builds.setChecked(get_show_daily_archive_builds())
        self.show_daily_archive_builds.clicked.connect(self.toggle_show_daily_archive_builds)
        self.show_experimental_archive_builds = QCheckBox(self)
        self.show_experimental_archive_builds.setText("Show Experimental Archived Builds")
        self.show_experimental_archive_builds.setToolTip(
            "Show Experimental Archived Builds\
            \nDEFAULT: Off"
        )
        self.show_experimental_archive_builds.setChecked(get_show_experimental_archive_builds())
        self.show_experimental_archive_builds.clicked.connect(self.toggle_show_experimental_archive_builds)
        self.show_patch_archive_builds = QCheckBox(self)
        self.show_patch_archive_builds.setText("Show Patch Archived Builds")
        self.show_patch_archive_builds.setToolTip(
            "Show Patch Archived Builds\
            \nDEFAULT: Off"
        )
        self.show_patch_archive_builds.setChecked(get_show_patch_archive_builds())
        self.show_patch_archive_builds.clicked.connect(self.toggle_show_patch_archive_builds)

        # Layout
        self.scraping_builds_layout = QGridLayout()
        self.scraping_builds_layout.addWidget(self.CheckForNewBuildsAutomatically, 0, 0, 1, 1)
        self.scraping_builds_layout.addWidget(self.NewBuildsCheckFrequency, 0, 1, 1, 1)
        self.scraping_builds_layout.addWidget(self.CheckForNewBuildsOnStartup, 1, 0, 1, 2)
        self.scraping_builds_layout.addWidget(QLabel("Minimum stable build to scrape", self), 2, 0, 1, 1)
        self.scraping_builds_layout.addWidget(self.MinStableBlenderVer, 2, 1, 1, 1)
        self.scraping_builds_layout.addWidget(self.show_daily_archive_builds, 3, 0, 1, 2)
        self.scraping_builds_layout.addWidget(self.show_experimental_archive_builds, 4, 0, 1, 2)
        self.scraping_builds_layout.addWidget(self.show_patch_archive_builds, 5, 0, 1, 2)
        self.buildcheck_settings.setLayout(self.scraping_builds_layout)

        # Downloading builds settings
        self.download_settings = SettingsGroup("Downloading & Saving Builds", parent=self)

        # Mark As Favorite
        self.EnableMarkAsFavorite = QCheckBox()
        self.EnableMarkAsFavorite.setText("Mark as Favorite")
        self.EnableMarkAsFavorite.setToolTip(
            "Mark a tab as favorite to quickly access it\
            \nDEFAULT: Off"
        )
        self.EnableMarkAsFavorite.setChecked(get_mark_as_favorite() != 0)
        self.EnableMarkAsFavorite.clicked.connect(self.toggle_mark_as_favorite)
        self.MarkAsFavorite = QComboBox()
        self.MarkAsFavorite.addItems([fav for fav in favorite_pages if fav != "Disable"])
        self.MarkAsFavorite.setToolTip(
            "Select a tab to mark as favorite\
            \nDEFAULT: Stable Releases"
        )
        self.MarkAsFavorite.setCurrentIndex(max(get_mark_as_favorite() - 1, 0))
        self.MarkAsFavorite.activated[int].connect(self.change_mark_as_favorite)
        self.MarkAsFavorite.setEnabled(self.EnableMarkAsFavorite.isChecked())

        # Install Template
        self.InstallTemplate = QCheckBox()
        self.InstallTemplate.setText("Install Template")
        self.InstallTemplate.setToolTip(
            "Installs a template on newly added builds to the Library tab\
            \nDEFAULT: Off"
        )
        self.InstallTemplate.clicked.connect(self.toggle_install_template)
        self.InstallTemplate.setChecked(get_install_template())

        self.downloading_layout = QGridLayout()
        self.downloading_layout.addWidget(self.EnableMarkAsFavorite, 0, 0, 1, 1)
        self.downloading_layout.addWidget(self.MarkAsFavorite, 0, 1, 1, 1)
        self.downloading_layout.addWidget(self.InstallTemplate, 1, 0, 1, 2)
        self.download_settings.setLayout(self.downloading_layout)

        # Launching builds settings
        self.launching_settings = SettingsGroup("Launching Builds", parent=self)

        # Quick Launch Key Sequence
        self.EnableQuickLaunchKeySeq = QCheckBox()
        self.EnableQuickLaunchKeySeq.setText("Quick Launch Global Shortcut")
        self.EnableQuickLaunchKeySeq.setToolTip(
            "Enable a global shortcut to quickly launch Blender\
            \nDEFAULT: On"
        )
        self.EnableQuickLaunchKeySeq.clicked.connect(self.toggle_enable_quick_launch_key_seq)
        self.EnableQuickLaunchKeySeq.setChecked(get_enable_quick_launch_key_seq())
        self.QuickLaunchKeySeq = QLineEdit()
        self.QuickLaunchKeySeq.setEnabled(get_enable_quick_launch_key_seq())
        self.QuickLaunchKeySeq.keyPressEvent = self._keyPressEvent
        self.QuickLaunchKeySeq.setText(str(get_quick_launch_key_seq()))
        self.QuickLaunchKeySeq.setToolTip(
            "Global shortcut to quickly launch Blender\
            \nDEFAULT: ctrl + f11"
        )
        self.QuickLaunchKeySeq.setContextMenuPolicy(Qt.NoContextMenu)
        self.QuickLaunchKeySeq.setCursorPosition(0)
        self.QuickLaunchKeySeq.editingFinished.connect(self.update_quick_launch_key_seq)
        # Run Blender using blender-launcher.exe
        self.LaunchBlenderNoConsole = QCheckBox()
        self.LaunchBlenderNoConsole.setText("Hide Console On Startup")
        self.LaunchBlenderNoConsole.setToolTip(
            "Hide the console window when launching Blender\
            \nDEFAULT: On"
        )
        self.LaunchBlenderNoConsole.clicked.connect(self.toggle_launch_blender_no_console)
        self.LaunchBlenderNoConsole.setChecked(get_launch_blender_no_console())
        # Blender Startup Arguments
        self.BlenderStartupArguments = QLineEdit()
        self.BlenderStartupArguments.setText(str(get_blender_startup_arguments()))
        self.BlenderStartupArguments.setToolTip(
            "Arguments to pass to when launching Blender (after the Blender executable i.e. [… <args>]\
            \nDEFAULT: None\
            \nExample: --background"
        )
        self.BlenderStartupArguments.setContextMenuPolicy(Qt.NoContextMenu)
        self.BlenderStartupArguments.setCursorPosition(0)
        self.BlenderStartupArguments.editingFinished.connect(self.update_blender_startup_arguments)
        # Command Line Arguments
        self.BashArguments = QLineEdit()
        self.BashArguments.setText(str(get_bash_arguments()))
        self.BashArguments.setToolTip(
            "Instructions to pass to bash when launching Blender (before the Blender executable i.e. [<args> …])\
            \nDEFAULT: None\
            \nExample: env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia nohup"
        )
        self.BashArguments.setContextMenuPolicy(Qt.NoContextMenu)
        self.BashArguments.setCursorPosition(0)
        self.BashArguments.editingFinished.connect(self.update_bash_arguments)

        self.launching_layout = QFormLayout()
        self.launching_layout.addRow(self.EnableQuickLaunchKeySeq, self.QuickLaunchKeySeq)
        if get_platform() == "Windows":
            self.launching_layout.addRow(self.LaunchBlenderNoConsole)
        if get_platform() == "Linux":
            self.launching_layout.addRow(QLabel("Bash Arguments:", self))
            self.launching_layout.addRow(self.BashArguments)

        self.launching_layout.addRow(QLabel("Startup Arguments:", self))
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
        MOD_MASK = Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier
        key_name = ""
        key = e.key()
        modifiers = int(e.modifiers())

        if (
            modifiers
            and modifiers & MOD_MASK == modifiers
            and key > 0
            and key not in {Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta}
        ):
            key_name = QtGui.QKeySequence(modifiers + key).toString()
        elif not modifiers and (key != Qt.Key_Meta):
            key_name = QtGui.QKeySequence(key).toString()

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
        set_new_builds_check_frequency(self.NewBuildsCheckFrequency.value() * 60)

    def toggle_check_on_startup(self, is_checked):
        set_check_for_new_builds_on_startup(is_checked)
        self.CheckForNewBuildsOnStartup.setChecked(is_checked)

    def toggle_scrape_stable_builds(self, is_checked):
        set_scrape_stable_builds(is_checked)

    def toggle_scrape_automated_builds(self, is_checked):
        set_scrape_automated_builds(is_checked)

    def toggle_scrape_bfa_builds(self, is_checked):
        set_scrape_bfa_builds(is_checked)

    def toggle_show_daily_archive_builds(self, is_checked):
        set_show_daily_archive_builds(is_checked)
        self.show_daily_archive_builds.setChecked(is_checked)

    def toggle_show_experimental_archive_builds(self, is_checked):
        set_show_experimental_archive_builds(is_checked)
        self.show_experimental_archive_builds.setChecked(is_checked)

    def toggle_show_patch_archive_builds(self, is_checked):
        set_show_patch_archive_builds(is_checked)
        self.show_patch_archive_builds.setChecked(is_checked)
