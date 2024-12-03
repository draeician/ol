"""Tests for version management functionality."""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from packaging import version

from ol.version import VersionManager, CACHE_DURATION

@pytest.fixture
def version_manager(tmp_path):
    """Create a version manager with temporary paths."""
    with patch('ol.version.Path.home') as mock_home:
        mock_home.return_value = tmp_path
        vm = VersionManager()
        yield vm

def test_version_info_initialization(version_manager, tmp_path):
    """Test that version info is properly initialized."""
    config_dir = tmp_path / '.config' / 'ol'
    version_file = config_dir / 'version.json'
    
    assert version_file.exists()
    with open(version_file) as f:
        info = json.load(f)
    
    assert 'version' in info
    assert 'last_check' in info
    assert 'check_frequency' in info
    assert 'check_updates' in info

def test_cache_management(version_manager):
    """Test cache loading and saving."""
    test_data = {'version': '1.0.0', 'notes_url': 'test_url'}
    version_manager._save_cache(test_data)
    
    cache = version_manager._load_cache()
    assert cache is not None
    assert cache['data'] == test_data
    assert 'timestamp' in cache

def test_cache_expiration(version_manager):
    """Test that expired cache is not used."""
    test_data = {'version': '1.0.0', 'notes_url': 'test_url'}
    version_manager._save_cache(test_data)
    
    # Modify timestamp to be expired
    cache_file = version_manager.version_cache
    with open(cache_file) as f:
        cache = json.load(f)
    cache['timestamp'] = time.time() - (CACHE_DURATION + 1)
    with open(cache_file, 'w') as f:
        json.dump(cache, f)
    
    assert version_manager._load_cache() is None

@patch('ol.version.requests.get')
def test_latest_version_fetching(mock_get, version_manager):
    """Test latest version fetching from pyproject.toml."""
    mock_response = MagicMock()
    mock_response.text = '''
[project]
name = "ol"
version = "1.0.0"
description = "A Python wrapper for the Ollama REPL command"
'''
    mock_get.return_value = mock_response
    
    latest = version_manager.fetch_latest_version()
    assert latest is not None
    assert latest['version'] == '1.0.0'
    assert 'CHANGELOG.md' in latest['html_url']
    assert latest['update_command'] == 'pipx reinstall git+https://github.com/draeician/ol.git'

@patch('ol.version.git.Repo')
def test_local_repository_check(mock_repo, version_manager):
    """Test local repository version checking."""
    mock_tag = MagicMock()
    mock_tag.commit.committed_datetime = time.time()
    mock_tag.__str__ = lambda x: 'v1.0.0'
    
    mock_repo.return_value.tags = [mock_tag]
    
    version = version_manager.check_local_repository()
    assert version == 'v1.0.0'

def test_version_comparison(version_manager):
    """Test version comparison logic."""
    with patch.object(version_manager, 'get_latest_version') as mock_get:
        mock_get.return_value = ('2.0.0', 'test_url', 'test_cmd')
        
        with patch('ol.version.current_version', '1.0.0'):
            update_available, latest, url, cmd = version_manager.check_for_updates()
            assert update_available is True
            assert latest == '2.0.0'
            assert url == 'test_url'
            assert cmd == 'test_cmd'

def test_update_message_formatting(version_manager):
    """Test update message formatting."""
    message = version_manager.format_update_message(
        '2.0.0',
        'https://github.com/test',
        'pip install test'
    )
    
    assert '2.0.0' in message
    assert 'pip install test' in message
    assert 'https://github.com/test' in message

def test_version_info_output(version_manager):
    """Test version info output formatting."""
    info = version_manager.get_version_info()
    assert 'ol version' in info
    assert 'github.com' in info 