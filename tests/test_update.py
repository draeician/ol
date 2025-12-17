import pytest
import subprocess
from unittest.mock import patch, MagicMock
from ol.cli import main


def test_update_command_no_shell_execution(mocker, capsys):
    """Test that update command uses argument list, not shell execution."""
    # Mock VersionManager
    mock_vm = MagicMock()
    mock_vm.check_for_updates.return_value = (
        True,  # update_available
        '0.1.25',  # latest_version
        'https://github.com/draeician/ol/blob/main/CHANGELOG.md',  # notes_url
        'pipx reinstall git+https://github.com/draeician/ol.git'  # update_cmd
    )
    mock_vm.format_update_message.return_value = "Update available: 0.1.24 → 0.1.25"
    
    mocker.patch('ol.cli.VersionManager', return_value=mock_vm)
    
    # Mock subprocess.run to verify it's called with argument list, not shell=True
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(returncode=0)
    
    # Call update
    main(['--update'])
    
    # Verify subprocess.run was called
    assert mock_run.called
    
    # Verify it was called with argument list (not shell=True)
    call_args = mock_run.call_args
    args = call_args[0][0]  # First positional argument
    
    # Should be a list, not a string
    assert isinstance(args, list)
    assert args == ['pipx', 'reinstall', 'git+https://github.com/draeician/ol.git']
    
    # Verify shell=False (or not specified, which defaults to False)
    kwargs = call_args[1]
    assert kwargs.get('shell', False) is False
    assert kwargs.get('check') is True


def test_update_command_handles_spaces_in_url(mocker, capsys):
    """Test that update command correctly handles URLs with special characters."""
    mock_vm = MagicMock()
    mock_vm.check_for_updates.return_value = (
        True,
        '0.1.25',
        None,
        'pipx reinstall "git+https://github.com/draeician/ol.git"'
    )
    mock_vm.format_update_message.return_value = "Update available"
    
    mocker.patch('ol.cli.VersionManager', return_value=mock_vm)
    
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(returncode=0)
    
    main(['--update'])
    
    # Verify command was parsed correctly
    call_args = mock_run.call_args
    args = call_args[0][0]
    assert isinstance(args, list)
    # shlex.split should handle quoted strings correctly
    assert 'pipx' in args
    assert 'reinstall' in args


def test_update_command_failure_surfaces_error(mocker, capsys):
    """Test that update command failures are surfaced correctly."""
    mock_vm = MagicMock()
    mock_vm.check_for_updates.return_value = (
        True,
        '0.1.25',
        None,
        'pipx reinstall git+https://github.com/draeician/ol.git'
    )
    mock_vm.format_update_message.return_value = "Update available"
    
    mocker.patch('ol.cli.VersionManager', return_value=mock_vm)
    
    # Mock subprocess.run to raise CalledProcessError
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=['pipx', 'reinstall', 'git+https://github.com/draeician/ol.git'],
        stderr='Error: package not found'
    )
    
    # Should exit with code 1
    with pytest.raises(SystemExit) as exc_info:
        main(['--update'])
    assert exc_info.value.code == 1
    
    # Verify error message was printed
    captured = capsys.readouterr()
    assert 'Error during update' in captured.err


def test_update_command_invalid_parsing_handled(mocker, capsys):
    """Test that invalid command parsing is handled gracefully."""
    mock_vm = MagicMock()
    mock_vm.check_for_updates.return_value = (
        True,
        '0.1.25',
        None,
        'invalid command with unclosed "quote'  # Invalid command that shlex.split might fail on
    )
    mock_vm.format_update_message.return_value = "Update available"
    
    mocker.patch('ol.cli.VersionManager', return_value=mock_vm)
    
    # Should exit with code 1 on parsing error
    with pytest.raises(SystemExit) as exc_info:
        main(['--update'])
    assert exc_info.value.code == 1
    
    # Verify error message was printed
    captured = capsys.readouterr()
    assert 'Error parsing update command' in captured.err or 'Error during update' in captured.err

