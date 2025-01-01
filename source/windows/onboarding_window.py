from __future__ import annotations

import logging
import os
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING

from modules.settings import set_first_time_setup_seen
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QWizard,
)
from widgets.onboarding_setup.wizard_pages import (
    AppearancePage,
    BackgroundRunningPage,
    BasicOnboardingPage,
    ChooseLibraryPage,
    CommittingPage,
    ErrorOccurredPage,
    PropogatedSettings,
    RepoSelectPage,
    ShortcutsPage,
    WelcomePage,
)
from windows.base_window import BaseWindow

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent
    from semver import Version
    from windows.main_window import BlenderLauncher


@dataclass
class Committer(QThread):
    pages: list[BasicOnboardingPage]

    def __post_init__(self):
        super().__init__()

    completed = Signal()
    err = Signal(tuple)

    def run(self):
        finished_pages = ""
        try:
            for page in self.pages:
                page.evaluate()
                txt = f'Finished page "{page.title()}"'
                logging.info(txt)
                finished_pages += txt + "\n"
            self.completed.emit()
        except Exception:
            # show the exception
            exc = traceback.format_exc()
            text = f'{finished_pages}\nERR OCCURRED DURING PAGE "{page.title()}"!\n{exc}'
            self.err.emit((exc, text))


class OnboardingWindow(BaseWindow):
    accepted = Signal()
    cancelled = Signal()

    def __init__(self, version: Version, parent: BlenderLauncher):
        super().__init__(parent=parent, version=version)
        self.setWindowTitle("Blender Launcher V2 First-Time Setup")
        self.setMinimumWidth(768)
        self.setMinimumHeight(512)
        self.parent_ = parent
        # A wizard showing the settings being configured
        self.wizard = QWizard(self)
        self.wizard.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.wizard.setPixmap(QWizard.WizardPixmap.LogoPixmap, parent.icons.taskbar.pixmap(64, 64))
        self.wizard.button(QWizard.WizardButton.NextButton).setProperty("CreateButton", True)  # type: ignore
        self.wizard.button(QWizard.WizardButton.BackButton).setProperty("CreateButton", True)  # type: ignore
        self.wizard.button(QWizard.WizardButton.CancelButton).setProperty("CancelButton", True)  # type: ignore
        self.wizard.button(QWizard.WizardButton.FinishButton).setProperty("LaunchButton", True)  # type: ignore

        # A wizard shown during the execution stage
        self.commit_wizard = QWizard(self)
        self.commit_wizard.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.commit_wizard.setButtonLayout([])

        # A wizard shown when an error occurs
        self.error_wizard = QWizard(self)
        self.error_wizard.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.error_wizard.button(QWizard.WizardButton.CancelButton).setProperty("CancelButton", True)
        self.error_wizard.button(QWizard.WizardButton.FinishButton).setProperty("LaunchButton", True)
        self.error_wizard.setButtonText(QWizard.WizardButton.FinishButton, "OK")

        self.prop_settings = PropogatedSettings()

        self.pages: list[BasicOnboardingPage] = [
            WelcomePage(version, self.prop_settings, parent),
            ChooseLibraryPage(self.prop_settings, parent),
            RepoSelectPage(self.prop_settings, parent),
            ShortcutsPage(self.prop_settings, parent),
            AppearancePage(self.prop_settings, parent),
            BackgroundRunningPage(self.prop_settings, parent),
        ]

        for page in self.pages:
            self.wizard.addPage(page)

        self.committer = Committer(self.pages)
        self.committer.completed.connect(self.__commiter_completed)
        self.committer.err.connect(self.__commiter_errored)
        self.committing_page = CommittingPage(parent)
        self.commit_wizard.addPage(self.committing_page)
        self.error_page = ErrorOccurredPage(parent)
        self.error_wizard.addPage(self.error_page)

        widget = QWidget(self)
        self.central_layout = QVBoxLayout(widget)
        self.central_layout.setContentsMargins(1, 1, 1, 1)
        self.central_layout.addWidget(self.wizard)
        self.central_layout.addWidget(self.commit_wizard)
        self.central_layout.addWidget(self.error_wizard)

        self.setCentralWidget(widget)

        self.wizard.accepted.connect(self.__accepted)
        self.wizard.rejected.connect(self.__rejected)
        self.error_wizard.accepted.connect(self.__accept_ignore_errors)
        self.error_wizard.rejected.connect(self.__rejected)
        self._rejected = False
        self._accepted = False
        self.commit_wizard.hide()
        self.error_wizard.hide()

    def __accepted(self):
        # Run all of the page evaluation
        self.wizard.hide()
        self.commit_wizard.show()
        self.committer.start()

    def __commiter_completed(self):
        self.accepted.emit()
        self._accepted = True
        set_first_time_setup_seen(True)
        if self.prop_settings.exe_changed:
            self.parent_.restart_app(self.prop_settings.exe_location.parent)
        self.close()

    def __commiter_errored(self, exc_str):
        self.commit_wizard.hide()
        exc, s = exc_str
        logging.error(exc)
        self.error_page.output.setText(s)
        self.error_wizard.show()

    def __rejected(self):
        self.cancelled.emit()
        self._rejected = True
        self.close()

    def __accept_ignore_errors(self):
        self.accepted.emit()
        self._accepted = True
        set_first_time_setup_seen(True)
        self.close()

    def closeEvent(self, event: QCloseEvent):
        if self._accepted:
            event.accept()
            return

        if not self._rejected:
            event.ignore()
            self.__rejected()
