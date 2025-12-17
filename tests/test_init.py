import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_import_does_not_create_config_dir(tmp_path, monkeypatch):
    """Test that importing the package does not write to ~/.config/ol."""
    # Mock Path.home to return our tmp_path
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    config_dir = tmp_path / '.config' / 'ol'
    
    # Import the package
    import ol
    
    # Verify config directory was NOT created
    assert not config_dir.exists()
    assert not (config_dir / 'config.yaml').exists()


def test_import_does_not_initialize(tmp_path, monkeypatch):
    """Test that importing ol does not call initialize_ol."""
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    # Mock initialize_ol to track if it's called
    with patch('ol.init.initialize_ol') as mock_init:
        # Import the package
        import ol
        
        # Verify initialize_ol was NOT called on import
        mock_init.assert_not_called()


def test_cli_invocation_initializes(tmp_path, monkeypatch):
    """Test that CLI invocation still initializes configuration."""
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    config_dir = tmp_path / '.config' / 'ol'
    
    # Import and call main (CLI execution)
    from ol.cli import main
    
    # Call main with version flag (exits early, but initialization happens first)
    try:
        main(['--version'])
    except SystemExit:
        pass
    
    # Verify config directory WAS created by CLI invocation
    assert config_dir.exists()
    assert (config_dir / 'config.yaml').exists()


def test_cli_invocation_creates_all_directories(tmp_path, monkeypatch):
    """Test that CLI invocation creates all required directories and files."""
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    config_dir = tmp_path / '.config' / 'ol'
    
    from ol.cli import main
    
    # Call main with version flag (exits early, but initialization happens)
    try:
        main(['--version'])
    except SystemExit:
        pass
    
    # Verify all directories and files are created
    assert config_dir.exists()
    assert (config_dir / 'config.yaml').exists()
    assert (config_dir / 'history.yaml').exists()
    assert (config_dir / 'templates').exists()
    assert (config_dir / 'cache').exists()


def test_multiple_imports_do_not_initialize(tmp_path, monkeypatch):
    """Test that multiple imports do not cause multiple initializations."""
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    config_dir = tmp_path / '.config' / 'ol'
    
    # Import multiple times
    import ol
    import ol.cli
    import ol.config
    
    # Verify config directory was NOT created
    assert not config_dir.exists()


def test_cli_initialization_happens_once(tmp_path, monkeypatch):
    """Test that CLI initialization happens but only when CLI is invoked."""
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    config_dir = tmp_path / '.config' / 'ol'
    
    # First, verify import doesn't create it
    import ol
    assert not config_dir.exists()
    
    # Then verify CLI invocation does create it
    from ol.cli import main
    try:
        main(['--version'])
    except SystemExit:
        pass
    
    assert config_dir.exists()

