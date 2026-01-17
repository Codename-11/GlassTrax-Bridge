"""
GlassTrax API Agent - Auto-Updater

Checks GitHub Releases for new versions and downloads/installs updates.
"""

import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from agent import __version__

logger = logging.getLogger("agent.updater")

# GitHub configuration
GITHUB_OWNER = "codename-11"
GITHUB_REPO = "GlassTrax-Bridge"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"

# Asset patterns for installer
ASSET_PATTERNS = [
    r".*-Setup\.exe$",
    r".*_setup\.exe$",
    r".*-Installer\.exe$",
]


@dataclass
class ReleaseInfo:
    """Information about a GitHub release"""

    version: str
    tag_name: str
    name: str
    body: str
    html_url: str
    asset_url: str | None
    asset_name: str | None
    published_at: str


def parse_version(version_str: str) -> tuple[int, int, int, str]:
    """
    Parse version string into comparable tuple.

    Handles formats: v1.0.0, 1.0.0, 1.0.0-beta, 1.0.0-rc.1
    Returns: (major, minor, patch, prerelease)
    """
    # Strip leading 'v' if present
    version_str = version_str.lstrip("v").strip()

    # Split on hyphen to separate prerelease
    parts = version_str.split("-", 1)
    version_part = parts[0]
    prerelease = parts[1] if len(parts) > 1 else ""

    # Parse major.minor.patch
    version_nums = version_part.split(".")
    try:
        major = int(version_nums[0]) if len(version_nums) > 0 else 0
        minor = int(version_nums[1]) if len(version_nums) > 1 else 0
        patch = int(version_nums[2]) if len(version_nums) > 2 else 0
    except ValueError:
        major, minor, patch = 0, 0, 0

    return (major, minor, patch, prerelease)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    p1 = parse_version(v1)
    p2 = parse_version(v2)

    # Compare major, minor, patch
    for i in range(3):
        if p1[i] < p2[i]:
            return -1
        if p1[i] > p2[i]:
            return 1

    # Compare prerelease (empty string means stable, which is higher)
    pre1, pre2 = p1[3], p2[3]
    if pre1 and not pre2:
        return -1  # v1 is prerelease, v2 is stable
    if not pre1 and pre2:
        return 1  # v1 is stable, v2 is prerelease
    if pre1 < pre2:
        return -1
    if pre1 > pre2:
        return 1

    return 0


class UpdateChecker:
    """
    Checks for updates from GitHub Releases and manages downloads.

    Usage:
        checker = UpdateChecker(
            on_update_available=lambda info: print(f"Update: {info.version}"),
            on_check_complete=lambda has_update: print(f"Check done: {has_update}"),
        )
        checker.check_async()  # Non-blocking check
        # or
        info = checker.check_sync()  # Blocking check
    """

    def __init__(
        self,
        on_update_available: Callable[[ReleaseInfo], None] | None = None,
        on_check_complete: Callable[[bool], None] | None = None,
        on_download_progress: Callable[[int, int], None] | None = None,
        on_download_complete: Callable[[Path], None] | None = None,
        on_download_failed: Callable[[str], None] | None = None,
    ):
        """
        Initialize the update checker.

        Args:
            on_update_available: Called when a new version is found
            on_check_complete: Called when check finishes (bool: update available)
            on_download_progress: Called during download (bytes_downloaded, total_bytes)
            on_download_complete: Called when download finishes successfully
            on_download_failed: Called when download fails (error message)
        """
        self.current_version = __version__
        self.latest_release: ReleaseInfo | None = None
        self.update_available = False

        # Callbacks
        self._on_update_available = on_update_available
        self._on_check_complete = on_check_complete
        self._on_download_progress = on_download_progress
        self._on_download_complete = on_download_complete
        self._on_download_failed = on_download_failed

        # State
        self._checking = False
        self._downloading = False
        self._download_path: Path | None = None

    def check_sync(self, timeout: float = 10.0) -> ReleaseInfo | None:
        """
        Check for updates synchronously (blocking).

        Returns:
            ReleaseInfo if update available, None otherwise
        """
        if self._checking:
            return None

        self._checking = True
        try:
            logger.info(f"Checking for updates (current: v{self.current_version})")

            with httpx.Client(timeout=timeout) as client:
                response = client.get(
                    GITHUB_API_URL,
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": f"GlassTrax-Bridge-Agent/{self.current_version}",
                    },
                )

                if response.status_code == 404:
                    logger.info("No releases found")
                    self._invoke_check_complete(False)
                    return None

                response.raise_for_status()
                data = response.json()

            # Parse release info
            tag_name = data.get("tag_name", "")
            version = tag_name.lstrip("v")

            # Find installer asset
            asset_url = None
            asset_name = None
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                for pattern in ASSET_PATTERNS:
                    if re.match(pattern, name, re.IGNORECASE):
                        asset_url = asset.get("browser_download_url")
                        asset_name = name
                        break
                if asset_url:
                    break

            release = ReleaseInfo(
                version=version,
                tag_name=tag_name,
                name=data.get("name", tag_name),
                body=data.get("body", ""),
                html_url=data.get("html_url", GITHUB_RELEASES_URL),
                asset_url=asset_url,
                asset_name=asset_name,
                published_at=data.get("published_at", ""),
            )

            # Compare versions
            if compare_versions(version, self.current_version) > 0:
                logger.info(f"Update available: v{version} (current: v{self.current_version})")
                self.latest_release = release
                self.update_available = True
                self._invoke_update_available(release)
                self._invoke_check_complete(True)
                return release
            else:
                logger.info(f"No update available (latest: v{version})")
                self.latest_release = release
                self.update_available = False
                self._invoke_check_complete(False)
                return None

        except httpx.TimeoutException:
            logger.warning("Update check timed out")
            self._invoke_check_complete(False)
            return None
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            self._invoke_check_complete(False)
            return None
        finally:
            self._checking = False

    def check_async(self, delay: float = 0) -> None:
        """
        Check for updates asynchronously (non-blocking).

        Args:
            delay: Seconds to wait before checking (default: 0)
        """
        def _check():
            if delay > 0:
                time.sleep(delay)
            self.check_sync()

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def download_update(self) -> None:
        """
        Download the update installer asynchronously.
        Calls on_download_complete or on_download_failed when done.
        """
        if not self.update_available or not self.latest_release:
            if self._on_download_failed:
                self._on_download_failed("No update available")
            return

        if not self.latest_release.asset_url:
            if self._on_download_failed:
                self._on_download_failed("No installer found in release")
            return

        if self._downloading:
            return

        def _download():
            self._downloading = True
            try:
                release = self.latest_release
                logger.info(f"Downloading update: {release.asset_name}")

                # Create temp file for download
                temp_dir = Path(tempfile.gettempdir())
                download_path = temp_dir / release.asset_name
                self._download_path = download_path

                with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                    with client.stream("GET", release.asset_url) as response:
                        response.raise_for_status()

                        total_size = int(response.headers.get("content-length", 0))
                        downloaded = 0

                        with open(download_path, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if self._on_download_progress and total_size > 0:
                                    self._on_download_progress(downloaded, total_size)

                logger.info(f"Download complete: {download_path}")

                if self._on_download_complete:
                    self._on_download_complete(download_path)

            except Exception as e:
                logger.error(f"Download failed: {e}")
                if self._on_download_failed:
                    self._on_download_failed(str(e))
            finally:
                self._downloading = False

        thread = threading.Thread(target=_download, daemon=True)
        thread.start()

    def install_update(self, installer_path: Path | None = None) -> bool:
        """
        Launch the installer and exit the application.

        Args:
            installer_path: Path to installer (uses last download if not provided)

        Returns:
            True if installer was launched, False otherwise
        """
        path = installer_path or self._download_path
        if not path or not path.exists():
            logger.error("No installer found to run")
            return False

        try:
            logger.info(f"Launching installer: {path}")
            # Use subprocess.Popen to start installer independently
            subprocess.Popen(
                [str(path)],
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to launch installer: {e}")
            return False

    def _invoke_update_available(self, release: ReleaseInfo) -> None:
        """Safely invoke on_update_available callback"""
        if self._on_update_available:
            try:
                self._on_update_available(release)
            except Exception as e:
                logger.error(f"Error in on_update_available callback: {e}")

    def _invoke_check_complete(self, has_update: bool) -> None:
        """Safely invoke on_check_complete callback"""
        if self._on_check_complete:
            try:
                self._on_check_complete(has_update)
            except Exception as e:
                logger.error(f"Error in on_check_complete callback: {e}")

    @staticmethod
    def get_releases_url() -> str:
        """Get the GitHub releases page URL"""
        return GITHUB_RELEASES_URL
