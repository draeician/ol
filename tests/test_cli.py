import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from ol.cli import main, get_env, is_image_file, get_file_type_and_prompt, format_shell_command

def test_help(capsys):
    """Test that help output works."""
    with pytest.raises(SystemExit):
        main(['--help'])
    captured = capsys.readouterr()
    assert 'Ollama REPL wrapper' in captured.out

def test_list_models(mocker):
    """Test that list models works."""
    mock_run = mocker.patch('subprocess.run')
    main(['-l'])
    mock_run.assert_called_once_with(['ollama', 'list'], env=mocker.ANY, check=True)

def test_run_with_model(mocker):
    """Test running with a specific model."""
    mock_run = mocker.patch('subprocess.run')
    main(['-m', 'codellama', 'test prompt'])
    mock_run.assert_called_once_with(
        ['ollama', 'run', 'codellama'],
        input=b'test prompt',
        env=mocker.ANY,
        check=True
    )

def test_debug_output(mocker, capsys, tmp_path):
    """Test debug output with file processing."""
    mock_run = mocker.patch('subprocess.run')
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    main(['-d', '-m', 'llama3.2', 'test prompt', str(test_file)])
    
    captured = capsys.readouterr()
    debug_output = captured.out
    
    assert "=== Debug Information ===" in debug_output
    assert "Model: llama3.2" in debug_output
    assert "Base Prompt: test prompt" in debug_output
    assert "Added content from" in debug_output
    assert "=== Command Information ===" in debug_output
    
    mock_run.assert_called_once_with(
        ['ollama', 'run', 'llama3.2'],
        input=mocker.ANY,
        env=mocker.ANY,
        check=True
    )

# Error Handling Tests
def test_ollama_command_failure(mocker):
    """Test behavior when Ollama command fails."""
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(1, ['ollama'])
    
    with pytest.raises(SystemExit) as exc_info:
        main(['-m', 'invalid_model', 'test'])
    assert exc_info.value.code == 1

def test_file_not_found(tmp_path):
    """Test behavior when file is not found."""
    non_existent = tmp_path / "does_not_exist.txt"
    with pytest.raises(SystemExit) as exc_info:
        main(['test prompt', str(non_existent)])
    assert exc_info.value.code == 1

def test_file_not_readable(tmp_path):
    """Test behavior when file is not readable."""
    test_file = tmp_path / "unreadable.txt"
    test_file.write_text("content")
    test_file.chmod(0o000)  # Remove all permissions
    
    with pytest.raises(SystemExit) as exc_info:
        main(['test prompt', str(test_file)])
    assert exc_info.value.code == 1
    
    test_file.chmod(0o644)  # Restore permissions for cleanup

# Configuration Tests
def test_model_selection_for_file_types(mocker, tmp_path):
    """Test model selection logic for different file types."""
    mock_run = mocker.patch('subprocess.run')
    
    # Test text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("content")
    main(['-m', 'llama2', 'test', str(text_file)])
    assert mock_run.call_args[0][0] == ['ollama', 'run', 'llama2']
    
    # Test image file
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    main(['-m', 'llava', 'test', str(image_file)])
    assert mock_run.call_args[0][0] == ['ollama', 'run', 'llava']

def test_default_prompts(mocker, tmp_path):
    """Test default prompt selection for different file types."""
    config = MagicMock()
    config.get_model_for_type.return_value = "llama2"
    mocker.patch('ol.cli.Config', return_value=config)
    mock_run = mocker.patch('subprocess.run')
    
    text_file = tmp_path / "test.txt"
    text_file.write_text("content")
    main(['analyze', str(text_file)])
    
    # Verify ollama was called with the correct input
    assert mock_run.call_count == 1
    call_args = mock_run.call_args
    assert call_args[0][0] == ['ollama', 'run', 'llama2']
    assert b'analyze' in call_args[1]['input']
    assert b'content' in call_args[1]['input']

def test_missing_config(mocker):
    """Test behavior when config file is missing."""
    mock_config = MagicMock()
    mock_config.get_model_for_type.return_value = "llama2"
    mocker.patch('ol.cli.Config', return_value=mock_config)
    mock_run = mocker.patch('subprocess.run')
    
    main(['test prompt'])
    
    mock_run.assert_called_once()

def test_ollama_host_handling(mocker):
    """Test OLLAMA_HOST environment variable handling."""
    mock_run = mocker.patch('subprocess.run')
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        main(['test prompt'])
        assert mock_run.call_args[1]['env']['OLLAMA_HOST'] == 'http://test:11434'

# Image Processing Tests
def test_image_processing_local(mocker, tmp_path):
    """Test handling of local image files."""
    mock_run = mocker.patch('subprocess.run')
    mock_popen = mocker.patch('subprocess.Popen')
    mock_popen.return_value.stdout = MagicMock()
    mock_popen.return_value.stderr = MagicMock()
    mock_popen.return_value.returncode = 0
    mock_popen.return_value.wait.return_value = 0
    
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    
    # Mock environment to ensure local processing
    with patch.dict(os.environ, {}, clear=True):
        main(['-m', 'llava', 'describe', str(image_file)])
    
    # Verify base64 and ollama processes were created
    assert mock_popen.call_count == 2
    
    # Verify correct commands were used
    calls = mock_popen.call_args_list
    assert calls[0][0][0][0] == 'base64'  # First call should be base64
    assert calls[1][0][0][0] == 'ollama'  # Second call should be ollama

def test_image_processing_remote(mocker, tmp_path):
    """Test handling of remote image files."""
    mock_run = mocker.patch('subprocess.run')
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b'fake_image_data')
        
        main(['-m', 'llava', 'describe', str(image_file)])
        
        # Verify single ollama process with image path
        mock_run.assert_called_once()
        assert b'describe' in mock_run.call_args[1]['input']

def test_mixed_content(mocker, tmp_path):
    """Test handling of mixed content (images + text)."""
    mock_run = mocker.patch('subprocess.run')
    
    text_file = tmp_path / "test.txt"
    text_file.write_text("content")
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    
    main(['-m', 'llama2', 'test', str(text_file), str(image_file)])
    
    # Should use text model for mixed content
    assert mock_run.call_args[0][0] == ['ollama', 'run', 'llama2']

# Input Processing Tests
def test_multiple_files(mocker, tmp_path):
    """Test handling of multiple files."""
    mock_run = mocker.patch('subprocess.run')
    
    files = []
    for i in range(3):
        f = tmp_path / f"test{i}.txt"
        f.write_text(f"content{i}")
        files.append(str(f))
    
    main(['-m', 'llama2', 'test'] + files)
    
    # Verify all files were included in input
    input_data = mock_run.call_args[1]['input'].decode()
    assert all(f"content{i}" in input_data for i in range(3))

def test_special_characters(mocker, tmp_path):
    """Test handling of file paths with special characters."""
    mock_run = mocker.patch('subprocess.run')
    
    file_path = tmp_path / "test with spaces!@#$.txt"
    file_path.write_text("content")
    
    main(['-m', 'llama2', 'test', str(file_path)])
    
    # Verify the file was processed correctly
    assert mock_run.called
    assert b'content' in mock_run.call_args[1]['input']

def test_path_handling(mocker, tmp_path):
    """Test handling of relative vs absolute paths."""
    mock_run = mocker.patch('subprocess.run')
    
    # Test absolute path
    abs_file = tmp_path / "abs_test.txt"
    abs_file.write_text("abs content")
    main(['-m', 'llama2', 'test', str(abs_file)])
    assert b'abs content' in mock_run.call_args[1]['input']
    
    # Test relative path
    with patch('os.getcwd', return_value=str(tmp_path)):
        rel_file = Path("rel_test.txt")
        (tmp_path / rel_file).write_text("rel content")
        main(['-m', 'llama2', 'test', str(rel_file)])
        assert b'rel content' in mock_run.call_args[1]['input']

# Remote Server Tests
def test_remote_connection(mocker):
    """Test connection to remote Ollama server."""
    mock_run = mocker.patch('subprocess.run')
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        main(['test prompt'])
        assert mock_run.call_args[1]['env']['OLLAMA_HOST'] == 'http://test:11434'

def test_remote_connection_error(mocker):
    """Test error handling for connection issues."""
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(1, ['ollama'])
    
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://invalid:11434'}):
        with pytest.raises(SystemExit) as exc_info:
            main(['test prompt'])
        assert exc_info.value.code == 1

def test_ollama_host_url_formatting():
    """Test URL formatting for OLLAMA_HOST."""
    # Test with http://
    with patch.dict(os.environ, {'OLLAMA_HOST': 'test:11434'}):
        env = get_env()
        assert env['OLLAMA_HOST'] == 'http://test:11434'
    
    # Test with existing http://
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        env = get_env()
        assert env['OLLAMA_HOST'] == 'http://test:11434'

# Command Formatting Tests
def test_shell_command_formatting():
    """Test shell command formatting with various inputs."""
    # Basic command
    cmd = ['ollama', 'run', 'model']
    result = format_shell_command(cmd, 'test prompt')
    assert 'echo' in result
    assert 'ollama run model' in result
    
    # Command with env vars
    result = format_shell_command(cmd, 'test', {'VAR': 'value'})
    assert 'export VAR=' in result
    
    # Command with special characters
    cmd = ['ollama', 'run', 'model with spaces']
    result = format_shell_command(cmd, 'test "quoted" prompt')
    assert 'model with spaces' in result
    assert '"quoted"' in result 

def test_version_flag(capsys):
    """Test that version flag works."""
    main(['--version'])
    captured = capsys.readouterr()
    assert 'ol version' in captured.out
    assert 'github.com' in captured.out 