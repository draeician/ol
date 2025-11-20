import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from ol.cli import main, get_env, is_image_file, get_file_type_and_prompt, format_shell_command, save_modelfile, save_all_modelfiles, list_installed_models, sanitize_model_name

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
    assert mock_run.call_args_list[0][0][0] == ['ollama', 'run', 'llama2']
    
    # Test image file
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    main(['-m', 'llava', 'test', str(image_file)])
    
    # Verify ollama was called with the image file path
    assert mock_run.call_args_list[1][0][0] == ['ollama', 'run', 'llava', 'test', str(image_file)]

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
    
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    
    # Mock environment to ensure local processing
    with patch.dict(os.environ, {}, clear=True):
        main(['-m', 'llava', 'describe', str(image_file)])
    
    # Verify ollama was called with the image file path
    mock_run.assert_called_once_with(
        ['ollama', 'run', 'llava', 'describe', str(image_file)],
        env=mocker.ANY,
        check=True
    )

def test_image_processing_remote(mocker, tmp_path):
    """Test handling of remote image files."""
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value.returncode = 0  # Ensure success
    
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b'fake_image_data')
        
        main(['-m', 'llava', 'describe', str(image_file)])
        
        # Verify ollama was called with the image file path
        mock_run.assert_called_once_with(
            ['ollama', 'run', 'llava', 'describe', str(image_file)],
            env=mocker.ANY,
            check=True
        )

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

def test_save_modelfile_success(mocker, tmp_path, monkeypatch):
    """Test successful Modelfile save."""
    # Mock subprocess.run
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2\nPARAMETER temperature 0.7"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    # Mock hostname and timestamp for predictable filename
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    # Change to tmp_path
    monkeypatch.chdir(tmp_path)
    
    result_path = save_modelfile('llama3.2', None, False)
    
    # Verify subprocess was called correctly
    mock_run.assert_called_once_with(
        ['ollama', 'show', '--modelfile', 'llama3.2'],
        capture_output=True,
        text=True,
        env=mocker.ANY,
        check=True
    )
    
    # Verify file was created with correct pattern
    assert result_path.exists()
    assert 'llama3.2' in result_path.name
    assert 'testhost' in result_path.name
    assert result_path.suffix == '.modelfile'
    
    # Verify content
    with open(result_path, 'r') as f:
        content = f.read()
        assert 'FROM llama3.2' in content
        assert 'PARAMETER temperature 0.7' in content

def test_save_modelfile_requires_model(capsys):
    """Test that --save-modelfile requires --model."""
    with pytest.raises(SystemExit) as exc_info:
        save_modelfile('', None, False)
    assert exc_info.value.code == 1
    
    captured = capsys.readouterr()
    assert '--model is required' in captured.err

def test_save_modelfile_remote_env(mocker, tmp_path, monkeypatch):
    """Test that OLLAMA_HOST is passed through to subprocess."""
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://remote:11434'}):
        save_modelfile('llama3.2', None, False)
        
        # Verify env was passed
        call_env = mock_run.call_args[1]['env']
        assert call_env['OLLAMA_HOST'] == 'http://remote:11434'

def test_save_modelfile_error_path(mocker, tmp_path, monkeypatch, capsys):
    """Test error handling when subprocess fails."""
    # Mock subprocess to raise CalledProcessError
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=['ollama', 'show', '--modelfile', 'invalid'],
        stderr='Model not found'
    )
    
    monkeypatch.chdir(tmp_path)
    
    with pytest.raises(SystemExit) as exc_info:
        save_modelfile('invalid', None, False)
    assert exc_info.value.code == 1
    
    captured = capsys.readouterr()
    assert 'Error fetching Modelfile' in captured.err
    assert 'returncode 1' in captured.err
    assert 'Model not found' in captured.err

def test_save_modelfile_with_output_dir(mocker, tmp_path):
    """Test saving Modelfile to custom output directory."""
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    output_dir = tmp_path / 'custom_dir'
    result_path = save_modelfile('llama3.2', str(output_dir), False)
    
    # Verify directory was created
    assert output_dir.exists()
    assert output_dir.is_dir()
    
    # Verify file is in the custom directory
    assert result_path.parent == output_dir
    assert result_path.exists()

def test_save_modelfile_colon_replacement(mocker, tmp_path, monkeypatch):
    """Test that colons in model name are replaced with underscores."""
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2:latest"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    result_path = save_modelfile('llama3.2:latest', None, False)
    
    # Verify filename has underscore instead of colon
    assert 'llama3.2_latest' in result_path.name
    assert ':' not in result_path.name

def test_sanitize_model_name():
    """Test model name sanitization."""
    # Test colon replacement
    assert sanitize_model_name('llama3.2:latest') == 'llama3.2_latest'
    
    # Test slash replacement
    assert sanitize_model_name('huggingface.co/unsloth/model') == 'huggingface.co_unsloth_model'
    
    # Test backslash replacement
    assert sanitize_model_name('model\\path') == 'model_path'
    
    # Test multiple problematic characters
    assert sanitize_model_name('model:with/slashes\\and|pipes') == 'model_with_slashes_and_pipes'
    
    # Test space replacement
    assert sanitize_model_name('model with spaces') == 'model_with_spaces'
    
    # Test multiple underscores collapse
    assert sanitize_model_name('model__with___underscores') == 'model_with_underscores'
    
    # Test leading/trailing dots
    assert sanitize_model_name('.model.') == 'model'

def test_save_modelfile_with_slashes(mocker, tmp_path, monkeypatch):
    """Test saving Modelfile with model name containing slashes."""
    mock_result = MagicMock()
    mock_result.stdout = "FROM huggingface.co/unsloth/model"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    model_name = 'huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF_Q8_K_XL'
    result_path = save_modelfile(model_name, None, False)
    
    # Verify file was created (no FileNotFoundError)
    assert result_path.exists()
    
    # Verify filename has slashes replaced
    assert '/' not in result_path.name
    assert 'huggingface.co_unsloth_Qwen3-Coder-30B-A3B-Instruct-GGUF_Q8_K_XL' in result_path.name

def test_save_all_modelfiles_handles_errors(mocker, tmp_path, monkeypatch, capsys):
    """Test that save_all_modelfiles continues on errors."""
    # Mock list_installed_models to return models including one with problematic name
    mocker.patch('ol.cli.list_installed_models', return_value=[
        'llama3.2',
        'huggingface.co/unsloth/problematic/model',  # This will cause issues
        'codellama'
    ])
    
    # Mock subprocess.run - first two succeed, third might fail
    mock_results = [
        MagicMock(stdout="FROM llama3.2", returncode=0),
        MagicMock(stdout="FROM problematic", returncode=0),
        MagicMock(stdout="FROM codellama", returncode=0),
    ]
    mock_run = mocker.patch('subprocess.run', side_effect=mock_results)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    # This should not raise an exception, but continue processing
    paths = save_all_modelfiles(None, False)
    
    # Should have saved at least some models
    assert len(paths) >= 2
    
    captured = capsys.readouterr()
    # Should have warnings for failed models if any
    # The function should continue and save what it can

def test_save_modelfile_main_integration(mocker, tmp_path, monkeypatch, capsys):
    """Test --save-modelfile flag in main() function."""
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    main(['--save-modelfile', '-m', 'llama3.2'])
    
    # Verify subprocess was called
    assert mock_run.called
    
    # Verify file was created
    captured = capsys.readouterr()
    assert '.modelfile' in captured.out

def test_all_flag_without_save_modelfile(capsys):
    """Test that --all without --save-modelfile errors."""
    with pytest.raises(SystemExit) as exc_info:
        main(['--all'])
    assert exc_info.value.code == 1
    
    captured = capsys.readouterr()
    assert '--all requires --save-modelfile' in captured.err

def test_list_installed_models_json(mocker):
    """Test list_installed_models with JSON output."""
    mock_result = MagicMock()
    mock_result.stdout = '[{"name": "llama3.2"}, {"name": "codellama"}]'
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    models = list_installed_models({}, False)
    
    assert 'llama3.2' in models
    assert 'codellama' in models
    assert len(models) == 2
    mock_run.assert_called_once_with(
        ['ollama', 'list', '--json'],
        env={},
        capture_output=True,
        text=True,
        check=True
    )

def test_list_installed_models_json_nested(mocker):
    """Test list_installed_models with nested JSON structure."""
    mock_result = MagicMock()
    mock_result.stdout = '{"models": [{"name": "llama3.2"}, {"name": "codellama"}]}'
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    models = list_installed_models({}, False)
    
    assert 'llama3.2' in models
    assert 'codellama' in models
    assert len(models) == 2

def test_list_installed_models_text_fallback(mocker):
    """Test list_installed_models falls back to text parsing."""
    # First call (JSON) fails
    # Second call (text) succeeds
    text_result = MagicMock()
    text_result.stdout = "NAME                ID      SIZE    MODIFIED\nllama3.2            abc123  4.7GB   2 hours ago\ncodellama           def456  3.2GB   1 day ago"
    text_result.returncode = 0
    
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = [
        subprocess.CalledProcessError(1, ['ollama'], stderr="Unknown flag"),
        text_result
    ]
    
    models = list_installed_models({}, False)
    
    assert 'llama3.2' in models
    assert 'codellama' in models
    assert len(models) == 2
    assert mock_run.call_count == 2

def test_save_all_modelfiles_success(mocker, tmp_path, monkeypatch, capsys):
    """Test saving Modelfiles for all models."""
    # Mock list_installed_models
    mocker.patch('ol.cli.list_installed_models', return_value=['llama3.2', 'codellama'])
    
    # Mock subprocess.run for show --modelfile
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    paths = save_all_modelfiles(None, False)
    
    # Verify two files were created
    assert len(paths) == 2
    assert all(p.exists() for p in paths)
    
    # Verify subprocess was called for each model
    assert mock_run.call_count == 2

def test_save_all_modelfiles_no_models(mocker, capsys):
    """Test save_all_modelfiles when no models are found."""
    mocker.patch('ol.cli.list_installed_models', return_value=[])
    
    with pytest.raises(SystemExit) as exc_info:
        save_all_modelfiles(None, False)
    assert exc_info.value.code == 1
    
    captured = capsys.readouterr()
    assert 'No models found' in captured.err

def test_save_all_modelfiles_main_integration(mocker, tmp_path, monkeypatch, capsys):
    """Test --save-modelfile --all in main() function."""
    # Mock list_installed_models
    mocker.patch('ol.cli.list_installed_models', return_value=['llama3.2', 'codellama'])
    
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mocker.patch('socket.gethostname', return_value='testhost')
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    main(['--save-modelfile', '--all'])
    
    # Verify subprocess was called multiple times (once per model)
    assert mock_run.call_count >= 2
    
    # Verify files were created
    captured = capsys.readouterr()
    assert '.modelfile' in captured.out
    # Should have multiple paths printed
    assert captured.out.count('.modelfile') >= 2

def test_host_port_override_env(mocker):
    """Test that -h and -p flags override OLLAMA_HOST environment variable."""
    mock_run = mocker.patch('subprocess.run')
    
    # Clear any existing OLLAMA_HOST
    with patch.dict(os.environ, {}, clear=True):
        main(['-h', 'example.com', '-p', '1234', 'test'])
        
        # Verify OLLAMA_HOST was set correctly
        assert mock_run.called
        call_env = mock_run.call_args[1]['env']
        assert call_env['OLLAMA_HOST'] == 'http://example.com:1234'

def test_host_only_default_port(mocker):
    """Test that -h flag uses default port 11434."""
    mock_run = mocker.patch('subprocess.run')
    
    with patch.dict(os.environ, {}, clear=True):
        main(['-h', 'example.com', 'test'])
        
        assert mock_run.called
        call_env = mock_run.call_args[1]['env']
        assert call_env['OLLAMA_HOST'] == 'http://example.com:11434'

def test_port_only_default_host(mocker):
    """Test that -p flag uses default host localhost."""
    mock_run = mocker.patch('subprocess.run')
    
    with patch.dict(os.environ, {}, clear=True):
        main(['-p', '12000', 'test'])
        
        assert mock_run.called
        call_env = mock_run.call_args[1]['env']
        assert call_env['OLLAMA_HOST'] == 'http://localhost:12000'

def test_help_still_works(capsys):
    """Test that --help and -? still work and are not shadowed by host flag."""
    # Test --help
    with pytest.raises(SystemExit):
        main(['--help'])
    captured = capsys.readouterr()
    assert 'Ollama REPL wrapper' in captured.out
    assert '-h' in captured.out or '--host' in captured.out
    assert '-p' in captured.out or '--port' in captured.out
    
    # Test -?
    with pytest.raises(SystemExit):
        main(['-?'])
    captured = capsys.readouterr()
    assert 'Ollama REPL wrapper' in captured.out

def test_save_modelfile_uses_ollama_host_hostname(mocker, tmp_path, monkeypatch):
    """Test that save_modelfile uses hostname from OLLAMA_HOST when set."""
    from ol.cli import save_modelfile
    
    mock_result = MagicMock()
    mock_result.stdout = "FROM llama3.2"
    mock_result.returncode = 0
    mock_run = mocker.patch('subprocess.run', return_value=mock_result)
    
    mock_datetime = mocker.patch('ol.cli.datetime')
    mock_now = MagicMock()
    mock_now.strftime.return_value = '20241220-120000'
    mock_datetime.now.return_value = mock_now
    
    monkeypatch.chdir(tmp_path)
    
    # Test with OLLAMA_HOST set
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://aether:11434'}):
        result_path = save_modelfile('llama3.2', None, False)
        
        # Verify filename contains 'aether' not local hostname
        assert 'aether' in result_path.name
        assert 'llama3.2' in result_path.name
        assert result_path.suffix == '.modelfile'
    
    # Test without OLLAMA_HOST (should use local hostname)
    mocker.patch('socket.gethostname', return_value='testhost')
    with patch.dict(os.environ, {}, clear=True):
        result_path = save_modelfile('llama3.2', None, False)
        
        # Verify filename contains local hostname
        assert 'testhost' in result_path.name
        assert 'llama3.2' in result_path.name