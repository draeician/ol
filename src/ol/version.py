"""Version management for ol."""

import json
import os
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import git
import requests
from packaging import version

from . import __version__ as current_version

GITHUB_RAW_URL = "https://raw.githubusercontent.com/draeician/ol/main/pyproject.toml"
CACHE_DURATION = 86400

def extract_version_from_pyproject(content: str) -> Optional[str]:
    """Extract version from pyproject.toml content."""
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None

class VersionManager:
    """Manages version checking and updates for ol."""

    def __init__(self, debug: bool = False):
        """Initialize the version manager."""
        self.config_dir = Path.home() / '.config' / 'ol'
        self.cache_dir = self.config_dir / 'cache'
        self.version_cache = self.cache_dir / 'version_check.json'
        self.version_info = self.config_dir / 'version.json'
        self.debug = debug
        
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize version info
        self._init_version_info()

    def _debug(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"DEBUG: {message}", file=sys.stderr)

    def _init_version_info(self) -> None:
        """Initialize or load version information."""
        if not self.version_info.exists():
            info = {
                'version': current_version,
                'last_check': None,
                'check_frequency': CACHE_DURATION,
                'check_updates': True
            }
            self._save_version_info(info)
        
    def _save_version_info(self, info: Dict) -> None:
        """Save version information to file."""
        try:
            with open(self.version_info, 'w') as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            print(f"Error saving version info: {e}")

    def _load_version_info(self) -> Dict:
        """Load version information from file."""
        try:
            with open(self.version_info, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                'version': current_version,
                'last_check': None,
                'check_frequency': CACHE_DURATION,
                'check_updates': True
            }

    def _load_cache(self) -> Optional[Dict]:
        """Load cached version information."""
        if not self.version_cache.exists():
            self._debug("No cache file found")
            return None
        
        try:
            with open(self.version_cache, 'r') as f:
                cache = json.load(f)
                # Check if cache is still valid
                time_since_check = time.time() - cache['timestamp']
                if time_since_check < CACHE_DURATION:
                    self._debug(f"Using cached version info (age: {time_since_check:.0f} seconds)")
                    return cache
                self._debug(f"Cache expired (age: {time_since_check:.0f} seconds)")
        except Exception as e:
            self._debug(f"Error reading cache: {e}")
        return None

    def _save_cache(self, data: Dict) -> None:
        """Save version information to cache."""
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        try:
            with open(self.version_cache, 'w') as f:
                json.dump(cache_data, f, indent=2)
                self._debug("Updated version cache")
        except Exception as e:
            print(f"Error saving cache: {e}")

    def fetch_latest_version(self) -> Optional[Dict]:
        """Fetch latest version information from GitHub."""
        self._debug(f"Fetching latest version from {GITHUB_RAW_URL}")
        try:
            response = requests.get(GITHUB_RAW_URL, timeout=5)
            response.raise_for_status()
            version_str = extract_version_from_pyproject(response.text)
            if version_str:
                self._debug(f"Found version {version_str} in pyproject.toml")
                return {
                    'version': version_str,
                    'html_url': 'https://github.com/draeician/ol/blob/main/CHANGELOG.md',
                    'update_command': 'pipx reinstall ol'
                }
            self._debug("Could not extract version from pyproject.toml")
        except requests.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404:
                self._debug("Could not fetch pyproject.toml from GitHub (404)")
            else:
                self._debug(f"Error fetching from GitHub: {e}")
            return None
        return None

    def check_local_repository(self) -> Optional[str]:
        """Check local git repository for version information."""
        self._debug("Checking local git repository for version")
        try:
            repo = git.Repo(search_parent_directories=True)
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
            if tags:
                version = str(tags[-1])
                self._debug(f"Found latest tag: {version}")
                return version
            self._debug("No tags found in local repository")
        except Exception as e:
            self._debug(f"Error checking local repository: {e}")
        return None

    def get_latest_version(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get the latest version information.
        
        Returns:
            Tuple of (version, release_notes_url, update_command)
        """
        # Check cache first
        self._debug("Checking for latest version")
        cache = self._load_cache()
        if cache:
            data = cache['data']
            self._debug(f"Using cached version: {data.get('version')}")
            return (
                data.get('version'),
                data.get('html_url'),
                data.get('update_command')
            )

        # Try fetching from GitHub
        latest = self.fetch_latest_version()
        if latest:
            self._save_cache(latest)
            return latest['version'], latest['html_url'], latest['update_command']

        # Try local repository as fallback
        self._debug("Trying local repository as fallback")
        local_version = self.check_local_repository()
        if local_version:
            version_str = local_version.lstrip('v')
            update_cmd = "pipx reinstall ol"
            self._save_cache({
                'version': version_str,
                'html_url': None,
                'update_command': update_cmd
            })
            return version_str, None, update_cmd

        self._debug("Could not determine latest version")
        return None, None, None

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Check if updates are available.
        
        Returns:
            Tuple of (update_available, latest_version, release_notes_url, update_command)
        """
        info = self._load_version_info()
        
        # Check if we should perform update check
        last_check = info.get('last_check')
        if last_check and time.time() - last_check < info['check_frequency']:
            time_since = time.time() - last_check
            self._debug(f"Skipping check (last check was {time_since:.0f} seconds ago)")
            return False, None, None, None

        # Update last check time
        info['last_check'] = time.time()
        self._save_version_info(info)

        self._debug(f"Current version: {current_version}")
        latest_version, notes_url, update_cmd = self.get_latest_version()
        if not latest_version:
            return False, None, None, None

        try:
            current = version.parse(current_version)
            latest = version.parse(latest_version)
            update_available = latest > current
            self._debug(f"Latest version: {latest_version} (update {'available' if update_available else 'not needed'})")
            return update_available, latest_version, notes_url, update_cmd
        except version.InvalidVersion:
            # If version parsing fails, try string comparison
            update_available = latest_version != current_version
            self._debug(f"Latest version: {latest_version} (using string comparison, update {'available' if update_available else 'not needed'})")
            return update_available, latest_version, notes_url, update_cmd

    def get_version_info(self) -> str:
        """Get formatted version information."""
        return f"""ol version {current_version}
Python package: https://github.com/draeician/ol
Report issues at: https://github.com/draeician/ol/issues"""

    def format_update_message(self, latest_version: str, notes_url: Optional[str], update_cmd: str) -> str:
        """Format update notification message."""
        msg = [
            f"Update available: {current_version} → {latest_version}",
            f"\nTo update, run: {update_cmd}"
        ]
        if notes_url:
            msg.append(f"\nRelease notes: {notes_url}")
        return "\n".join(msg) 