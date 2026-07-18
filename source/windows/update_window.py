from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
from typing import TypedDict

import distro
from modules.platform_utils import _check_call, _popen, get_cwd, get_platform, get_running_app_bundle
from modules.tasks import TaskQueue
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from threads.downloader import DownloadTask
from threads.extractor import ExtractTask
from threads.scraping.launcher_updates import get_release_tag
from widgets.base_progress_bar_widget import BaseProgressBarWidget
from windows.base_window import BaseWindow

release_link = "https://github.com/Victor-IX/Blender-Launcher-V2/releases/download/{0}/Blender_Launcher_{0}_{1}.zip"
api_link = "https://api.github.com/repos/Victor-IX/Blender-Launcher-V2/releases/tags/{}"

logger = logging.getLogger()


def release_asset_url(tag: str, platform: str) -> str:
    # macOS releases are published as "macos_arm64", everything else as "<Platform>_x64"
    suffix = "macos_arm64" if platform == "macOS" else f"{platform}_x64"
    return release_link.format(tag, suffix)


# this only shows relevant sections of the response
class GitHubAsset(TypedDict):
    url: str
    name: str
    browser_download_url: str


class GitHubRelease(TypedDict):
    assets: list[GitHubAsset]


class BlenderLauncherUpdater(BaseWindow):
    def __init__(self, app: QApplication, version, release_tag: str | None = None):
        super().__init__(app=app, version=version)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(256, 77)
        self.setWindowTitle("Updating Blender Launcher")

        self.CentralWidget = QWidget(self)
        self.CentralLayout = QVBoxLayout(self.CentralWidget)
        self.CentralLayout.setContentsMargins(3, 0, 3, 3)
        self.setCentralWidget(self.CentralWidget)

        self.HeaderLabel = QLabel("Updating Blender Launcher")
        self.HeaderLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ProgressBar = BaseProgressBarWidget(self)
        self.ProgressBar.setFixedHeight(36)
        self.CentralLayout.addWidget(self.HeaderLabel)
        self.CentralLayout.addWidget(self.ProgressBar)

        self._headers = {
            "X-GitHub-Api-Version": "2022-11-28",
        }

        self.platform = get_platform()
        self.cwd = get_cwd()

        # On macOS get_cwd() is inside the updater's own .app bundle, so the new
        # app must be installed next to it instead.
        self.install_dir = self.cwd
        if self.platform == "macOS":
            updater_bundle = get_running_app_bundle()
            if updater_bundle is not None:
                self.install_dir = updater_bundle.parent

        self.queue = TaskQueue(parent=self, worker_count=1)
        self.queue.start()

        if release_tag is None:
            assert self.manager is not None
            release_tag = get_release_tag(self.cm)
            if release_tag is None:
                # This is ok because release_tag can only be None when
                # update is invoked from CLI without a release tag
                raise RuntimeError("Failed to automatically determine the latest release tag!")

        self.release_tag = release_tag

        self.show()
        self.download()

    def get_link(self, response: GitHubRelease | None = None) -> str:
        assert self.manager is not None
        if response is None:
            api_req = api_link.format(self.release_tag)
            d = self.manager.request("GET", api_req, headers=self._headers)
            assert d.data is not None
            response = json.loads(d.data)
        assert response is not None

        assets = response["assets"]
        asset_table = {}  # {"<Distro>": asset}
        for asset in assets:
            if self.release_tag in asset["name"]:  # can never be so sure
                release_idx = asset["name"].find(self.release_tag) + len(self.release_tag) + 1
                asset_table[asset["name"][release_idx:-8]] = asset

        release = asset_table.get("Ubuntu", asset_table.get("Linux"))
        if release is None:
            return release_asset_url(self.release_tag, self.platform)

        for key in (
            distro.id().title(),
            distro.like().title(),
            distro.id(),
            distro.like(),
        ):
            if key in asset_table:
                release = asset_table[key]
                break

        return release["browser_download_url"]

    def download(self):
        # TODO
        # This function should not use proxy for downloading new builds!
        link = self.get_link() if self.platform == "Linux" else release_asset_url(self.release_tag, self.platform)

        assert self.manager is not None
        self.ProgressBar.set_state(self.ProgressBar.State.DOWNLOADING)
        a = DownloadTask(self.manager, link)
        a.progress.connect(self.ProgressBar.set_progress)
        a.finished.connect(self.extract)
        self.queue.append(a)

    def extract(self, source):
        self.ProgressBar.set_state(self.ProgressBar.State.EXTRACTING)
        self.source_zip = source

        dest = self.install_dir
        if self.platform == "macOS":
            # Extract into a staging folder so the installed app is only replaced
            # once extraction succeeds (a failed update never deletes it).
            self.staging_dir = self.install_dir / ".bl_update"
            if self.staging_dir.exists():
                shutil.rmtree(self.staging_dir, ignore_errors=True)
            self.staging_dir.mkdir(parents=True, exist_ok=True)
            dest = self.staging_dir

        a = ExtractTask(source, dest)
        a.progress.connect(self.ProgressBar.set_progress)
        a.finished.connect(self.finish)
        self.queue.append(a)

    def finish(self, dist, is_removed):
        # Clean up the downloaded zip file
        if self.source_zip.exists():
            try:
                self.source_zip.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {self.source_zip}: {e}")

        # Launch the freshly installed launcher and exit
        launcher = str(dist)
        if self.platform == "Windows":
            _popen([launcher], no_console=False)
        elif self.platform == "Linux":
            os.chmod(dist, 0o744)
            _popen('nohup "' + launcher + '"')
        elif self.platform == "macOS":
            launcher = str(self._install_macos_app(dist))
            with contextlib.suppress(Exception):
                _check_call(["xattr", "-dr", "com.apple.quarantine", launcher])
            # -n forces a new instance; the updater shares the new app's bundle id
            _popen(f'open -n "{launcher}"')
            updater_bundle = get_running_app_bundle()
            if updater_bundle is not None:
                _popen(f'sleep 3 && rm -rf "{updater_bundle.as_posix()}"')

        self.app.quit()

    def _install_macos_app(self, new_app):
        # Swap the staged app in for the installed one only after a successful
        # extraction, restoring the previous version if the swap itself fails.
        target = self.install_dir / new_app.name
        old = self.install_dir / f"{new_app.name}.old"
        shutil.rmtree(old, ignore_errors=True)
        if target.exists():
            target.rename(old)
        try:
            new_app.rename(target)
        except OSError:
            logger.exception("Failed to install update; restoring previous version")
            if not target.exists() and old.exists():
                old.rename(target)
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(self.staging_dir, ignore_errors=True)
        return target

    def closeEvent(self, event):
        self.queue.set_making_threads(False)
        self.queue.fullstop()
        event.accept()
