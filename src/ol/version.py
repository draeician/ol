"""Version management for ol."""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import git
import requests
from packaging import version

from . import __version__ as current_version

GITHUB_API_URL = "https://api.github.com/repos/draeician/ol/releases/latest"
CACHE_DURATION = 86400

class VersionManager:
    """Manages version checking and updates for ol."""

    def __init__(self):
        """Initialize the version manager."""
        self.config_dir = Path.home() / '.config' / 'ol'
        self.cache_dir = self.config_dir / 'cache'
        self.version_cache = self.cache_dir / 'version_check.json'
        self.version_info = self.config_dir / 'version.json'
        
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize version info
        self._init_version_info()

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
            return None
        
        try:
            with open(self.version_cache, 'r') as f:
                cache = json.load(f)
                # Check if cache is still valid
                if time.time() - cache['timestamp'] < CACHE_DURATION:
                    return cache
        except Exception:
            pass
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
        except Exception as e:
            print(f"Error saving cache: {e}")

    def fetch_github_release(self) -> Optional[Dict]:
        """Fetch latest release information from GitHub."""
        try:
            response = requests.get(GITHUB_API_URL, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching GitHub release: {e}")
            return None

    def check_local_repository(self) -> Optional[str]:
        """Check local git repository for version information."""
        try:
            repo = git.Repo(search_parent_directories=True)
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
            if tags:
                return str(tags[-1])
        except Exception:
            pass
        return None

    def get_latest_version(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get the latest version information.
        
        Returns:
            Tuple of (version, release_notes_url, update_command)
        """
        # Check cache first
        cache = self._load_cache()
        if cache:
            data = cache['data']
            return (
                data.get('version'),
                data.get('html_url'),
                data.get('update_command')
            )

        # Try GitHub API first (preferred method)
        release = self.fetch_github_release()
        if release:
            version_str = release['tag_name'].lstrip('v')
            update_cmd = "pipx reinstall ol"  # Always use pipx reinstall
            self._save_cache({
                'version': version_str,
                'html_url': release['html_url'],
                'update_command': update_cmd
            })
            return version_str, release['html_url'], update_cmd

        # Try local repository as fallback
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
            return False, None, None, None

        # Update last check time
        info['last_check'] = time.time()
        self._save_version_info(info)

        latest_version, notes_url, update_cmd = self.get_latest_version()
        if not latest_version:
            return False, None, None, None

        try:
            current = version.parse(current_version)
            latest = version.parse(latest_version)
            return latest > current, latest_version, notes_url, update_cmd
        except version.InvalidVersion:
            # If version parsing fails, try string comparison
            return latest_version != current_version, latest_version, notes_url, update_cmd

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