from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

from modules.settings import set_first_time_setup_seen
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QWizard,
)
from widgets.onboarding_setup.wizard_pages import (
    AppearancePage,
    BackgroundRunningPage,
    BasicOnboardingPage,
    ChooseLibraryPage,
    ErrorOccurredPage,
    FileAssociationPage,
    RepoSelectPage,
    WelcomePage,
)
from windows.base_window import BaseWindow

if TYPE_CHECKING:
    from PyQt5.QtGui import QCloseEvent
    from semver import Version
    from windows.main_window import BlenderLauncher

class OnboardingWindow(BaseWindow):
    accepted = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, version: Version, parent: BlenderLauncher):
        super().__init__(parent=parent, version=version)
        self.setWindowTitle("Blender Launcher V2 First-Time Setup")
        self.setMinimumWidth(768)
        self.setMinimumHeight(512)

        self.wizard = QWizard(self)
        self.wizard.setPixmap(QWizard.WizardPixmap.LogoPixmap, parent.icons.taskbar.pixmap(64, 64))
        self.wizard.button(QWizard.WizardButton.NextButton).setProperty("CreateButton", True)  # type: ignore
        self.wizard.button(QWizard.WizardButton.BackButton).setProperty("CreateButton", True)  # type: ignore
        self.wizard.button(QWizard.WizardButton.CancelButton).setProperty("CancelButton", True)  # type: ignore
        self.wizard.button(QWizard.WizardButton.FinishButton).setProperty("LaunchButton", True)  # type: ignore

        self.error_wizard = QWizard(self)
        self.error_wizard.button(QWizard.WizardButton.CancelButton).setProperty("CancelButton", True)  # type: ignore
        self.error_wizard.button(QWizard.WizardButton.FinishButton).setProperty("LaunchButton", True)  # type: ignore
        self.error_wizard.setButtonText(QWizard.WizardButton.FinishButton, "OK")

        self.error_page = ErrorOccurredPage(parent)
        self.error_wizard.addPage(self.error_page)
        self.error_wizard.hide()

        self.pages: list[BasicOnboardingPage] = [
            WelcomePage(version, parent),
            ChooseLibraryPage(parent),
            RepoSelectPage(parent),
            FileAssociationPage(parent),
            AppearancePage(parent),
            BackgroundRunningPage(parent),
        ]

        for page in self.pages:
            self.wizard.addPage(page)

        widget = QWidget(self)
        self.central_layout = QVBoxLayout(widget)
        self.central_layout.setContentsMargins(1, 1, 1, 1)
        self.central_layout.addWidget(self.wizard)
        self.central_layout.addWidget(self.error_wizard)

        self.setCentralWidget(widget)

        self.wizard.accepted.connect(self.__accepted)
        self.wizard.rejected.connect(self.__rejected)
        self.error_wizard.accepted.connect(self.__accept_ignore_errors)
        self.error_wizard.rejected.connect(self.__rejected)
        self._rejected = False
        self._accepted = False

    def __accepted(self):
        # Run all of the page evaluation
        self.wizard.hide()
        self.repaint()
        finished_pages = ""
        try:
            for page in self.pages:
                page.evaluate()
                finished_pages += f"Finished page {page.title()}\n"
        except Exception:
            # show the exception
            exc = traceback.format_exc()
            text = f'{finished_pages}\nERR OCCURRED DURING PAGE "{page.title()}"!\n{exc}'
            logging.error(exc)
            self.error_page.output.setText(text)
            self.error_wizard.show()
            return

        self.accepted.emit()
        self._accepted = True
        set_first_time_setup_seen(True)
        self.close()

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
