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
    """Build the GitHub release download URL for the launcher archive.

    The release assets are named per the build workflows:
      - Windows: ``Blender_Launcher_<tag>_Windows_x64.zip``
      - macOS:   ``Blender_Launcher_<tag>_macos_arm64.zip`` (lowercase, arm64 only)
    Linux is resolved separately via the GitHub API (distro-specific assets).
    """
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

        # On macOS the updater runs from inside its own .app bundle, so get_cwd()
        # (which is .../Updater.app/Contents/MacOS) is the wrong extraction target.
        # The new .app must land next to the installed app instead.
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

        # On macOS, remove the previous .app so ditto writes a clean bundle
        # instead of merging into stale files. The original app has already quit.
        if self.platform == "macOS":
            target = self.install_dir / "Blender Launcher.app"
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)

        a = ExtractTask(source, self.install_dir)
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
            _popen([launcher])
        elif self.platform == "Linux":
            os.chmod(dist, 0o744)
            _popen('nohup "' + launcher + '"')
        elif self.platform == "macOS":
            # Self-downloaded files are not quarantined, but strip the attribute
            # defensively so Gatekeeper never blocks the relaunch.
            with contextlib.suppress(Exception):
                _check_call(["xattr", "-dr", "com.apple.quarantine", launcher])
            # -n forces a new instance: the updater shares the new app's bundle
            # id, so without -n `open` would just re-activate this updater.
            _popen(f'open -n "{launcher}"')
            # Best-effort detached cleanup of this updater bundle copy.
            updater_bundle = get_running_app_bundle()
            if updater_bundle is not None:
                _popen(f'sleep 3 && rm -rf "{updater_bundle.as_posix()}"')

        self.app.quit()

    def closeEvent(self, event):
        self.queue.fullstop()
        event.accept()
