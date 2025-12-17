import pytest
import sys
from unittest.mock import patch, MagicMock
from io import StringIO
from ol.cli import main


def test_stdin_input_used_as_prompt(mocker, capsys):
    """Test that STDIN input is used as prompt when no prompt argument provided."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        b'{"response": "Response", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Simulate STDIN input
    stdin_content = "What is this code doing?"
    with patch('sys.stdin.isatty', return_value=False):
        with patch('sys.stdin.read', return_value=stdin_content):
            main([])
    
    # Verify API was called with STDIN content as prompt
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert payload['prompt'] == stdin_content


def test_stdin_combined_with_prompt_argument(mocker, capsys):
    """Test that STDIN input is combined with prompt argument when both provided."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        b'{"response": "Response", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Simulate STDIN input with prompt argument
    stdin_content = "Here is some code:\nprint('hello')"
    with patch('sys.stdin.isatty', return_value=False):
        with patch('sys.stdin.read', return_value=stdin_content):
            main(['Review this code'])
    
    # Verify API was called with combined prompt
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert stdin_content in payload['prompt']
    assert 'Review this code' in payload['prompt']


def test_stdin_with_files(mocker, tmp_path, capsys):
    """Test that STDIN input works with file arguments."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        b'{"response": "Response", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("file content")
    
    # Simulate STDIN input
    stdin_content = "Analyze this:"
    with patch('sys.stdin.isatty', return_value=False):
        with patch('sys.stdin.read', return_value=stdin_content):
            main([str(test_file)])
    
    # Verify API was called
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    # STDIN should be in prompt, file content should also be included
    assert stdin_content in payload['prompt']
    assert 'file content' in payload['prompt']


def test_no_stdin_when_tty(mocker, capsys):
    """Test that STDIN is not read when stdin is a TTY."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        b'{"response": "Response", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Simulate TTY (no STDIN available)
    with patch('sys.stdin.isatty', return_value=True):
        # Should show defaults when no args and no STDIN
        with pytest.raises(SystemExit):
            main([])
    
    # Verify API was NOT called (showed defaults instead)
    assert not mock_post.called


def test_stdin_multiline_input(mocker, capsys):
    """Test that STDIN handles multiline input correctly."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        b'{"response": "Response", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Simulate multiline STDIN input
    stdin_content = "Line 1\nLine 2\nLine 3"
    with patch('sys.stdin.isatty', return_value=False):
        with patch('sys.stdin.read', return_value=stdin_content):
            main([])
    
    # Verify API was called with multiline content
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'Line 1' in payload['prompt']
    assert 'Line 2' in payload['prompt']
    assert 'Line 3' in payload['prompt']


def test_stdin_empty_input(mocker, capsys):
    """Test that empty STDIN input is handled gracefully."""
    # Simulate empty STDIN
    with patch('sys.stdin.isatty', return_value=False):
        with patch('sys.stdin.read', return_value=""):
            # Should show defaults when no args and empty STDIN
            with pytest.raises(SystemExit):
                main([])
    
    # Should not crash, just show defaults


def test_stdin_trailing_newlines_removed(mocker, capsys):
    """Test that trailing newlines from STDIN are removed."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        b'{"response": "Response", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Simulate STDIN with trailing newlines
    stdin_content = "test content\n\n\n"
    with patch('sys.stdin.isatty', return_value=False):
        with patch('sys.stdin.read', return_value=stdin_content):
            main([])
    
    # Verify trailing newlines were removed
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    # Should not end with newlines
    assert not payload['prompt'].endswith('\n')
    assert payload['prompt'] == "test content"

