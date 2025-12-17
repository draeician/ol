import pytest
import os
import json
import subprocess
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from ol.cli import main, get_env, is_image_file, get_file_type_and_prompt, format_shell_command, save_modelfile, save_all_modelfiles, list_installed_models, sanitize_model_name

def create_mock_streaming_response(response_text, done=True):
    """Helper to create a mock streaming response with line-delimited JSON."""
    lines = [
        json.dumps({"response": chunk, "done": False})
        for chunk in response_text
    ]
    if done:
        lines.append(json.dumps({"response": "", "done": True}))
    return iter([line.encode('utf-8') for line in lines])

def test_help(capsys):
    """Test that help output works."""
    with pytest.raises(SystemExit):
        main(['--help'])
    captured = capsys.readouterr()
    assert 'Ollama REPL wrapper' in captured.out

def test_list_models(mocker):
    """Test that list models works (still uses subprocess)."""
    mock_run = mocker.patch('subprocess.run')
    main(['-l'])
    mock_run.assert_called_once_with(['ollama', 'list'], env=mocker.ANY, check=True)

def test_run_with_model(mocker, capsys):
    """Test running with a specific model via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Hello", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    main(['-m', 'codellama', 'test prompt'])
    
    # Verify requests.post was called
    assert mock_post.called
    call_args = mock_post.call_args
    
    # Verify endpoint URL
    assert call_args[0][0] == 'http://localhost:11434/api/generate'
    
    # Verify payload
    payload = call_args[1]['json']
    assert payload['model'] == 'codellama'
    assert payload['prompt'] == 'test prompt'
    assert payload['temperature'] == 0.7  # default temperature
    assert payload['stream'] is True
    assert 'images' not in payload
    
    # Verify output was printed
    captured = capsys.readouterr()
    assert 'Hello' in captured.out

def test_run_with_temperature(mocker, capsys):
    """Test running with custom temperature via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    main(['-m', 'llama3.2', '--temperature', '0.9', 'test prompt'])
    
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert payload['temperature'] == 0.9

def test_debug_output(mocker, capsys, tmp_path):
    """Test debug output with file processing via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    main(['-d', '-m', 'llama3.2', 'test prompt', str(test_file)])
    
    captured = capsys.readouterr()
    debug_output = captured.out
    
    assert "=== Debug Information ===" in debug_output
    assert "Model: llama3.2" in debug_output
    assert "Base Prompt: test prompt" in debug_output
    assert "Added content from" in debug_output
    assert "=== API Request ===" in debug_output
    
    # Verify API was called
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'test prompt' in payload['prompt']
    assert 'Test content' in payload['prompt']

# Error Handling Tests
def test_ollama_api_failure(mocker, capsys):
    """Test behavior when Ollama API call fails."""
    import requests
    mock_post = mocker.patch('requests.post')
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    
    with pytest.raises(SystemExit) as exc_info:
        main(['-m', 'invalid_model', 'test'])
    assert exc_info.value.code == 1
    
    captured = capsys.readouterr()
    assert 'Error calling Ollama API' in captured.err

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
def test_model_selection_for_file_types(mocker, tmp_path, capsys):
    """Test model selection logic for different file types via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Test text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("content")
    main(['-m', 'llama2', 'test', str(text_file)])
    
    # Verify API was called with text model
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert payload['model'] == 'llama2'
    assert 'images' not in payload
    
    # Test image file
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    mock_post.reset_mock()
    
    main(['-m', 'llava', 'test', str(image_file)])
    
    # Verify API was called with image
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert payload['model'] == 'llava'
    assert 'images' in payload
    assert len(payload['images']) == 1
    # Verify image is base64 encoded
    assert isinstance(payload['images'][0], str)
    assert len(payload['images'][0]) > 0

def test_default_prompts(mocker, tmp_path, capsys):
    """Test default prompt selection for different file types via HTTP API."""
    config = MagicMock()
    config.get_model_for_type.return_value = "llama2"
    config.get_temperature_for_type.return_value = 0.7
    mocker.patch('ol.cli.Config', return_value=config)
    
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    text_file = tmp_path / "test.txt"
    text_file.write_text("content")
    main(['analyze', str(text_file)])
    
    # Verify API was called
    assert mock_post.call_count == 1
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'analyze' in payload['prompt']
    assert 'content' in payload['prompt']

def test_missing_config(mocker, capsys):
    """Test behavior when config file is missing via HTTP API."""
    mock_config = MagicMock()
    mock_config.get_model_for_type.return_value = "llama2"
    mock_config.get_temperature_for_type.return_value = 0.7
    mocker.patch('ol.cli.Config', return_value=mock_config)
    
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    main(['test prompt'])
    
    assert mock_post.called

def test_ollama_host_handling(mocker, capsys):
    """Test OLLAMA_HOST environment variable handling via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        main(['test prompt'])
        
        # Verify endpoint URL uses OLLAMA_HOST
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://test:11434/api/generate'

# Image Processing Tests
def test_image_processing_local(mocker, tmp_path, capsys):
    """Test handling of local image files via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    
    # Mock environment to ensure local processing
    with patch.dict(os.environ, {}, clear=True):
        main(['-m', 'llava', 'describe', str(image_file)])
    
    # Verify API was called with image
    assert mock_post.called
    call_args = mock_post.call_args
    assert call_args[0][0] == 'http://localhost:11434/api/generate'
    payload = call_args[1]['json']
    assert 'images' in payload
    assert len(payload['images']) == 1
    # Verify image is base64 encoded
    decoded = base64.b64decode(payload['images'][0])
    assert decoded == b'fake_image_data'

def test_image_processing_remote(mocker, tmp_path, capsys):
    """Test handling of remote image files via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b'fake_image_data')
        
        main(['-m', 'llava', 'describe', str(image_file)])
        
        # Verify endpoint URL uses OLLAMA_HOST
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://test:11434/api/generate'
        payload = call_args[1]['json']
        assert 'images' in payload
        assert len(payload['images']) == 1

def test_mixed_content(mocker, tmp_path, capsys):
    """Test handling of mixed content (images + text) via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    text_file = tmp_path / "test.txt"
    text_file.write_text("content")
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    
    main(['-m', 'llama2', 'test', str(text_file), str(image_file)])
    
    # Should include both text content and images
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'content' in payload['prompt']  # Text file content in prompt
    assert 'images' in payload  # Images in payload
    assert len(payload['images']) == 1

# Input Processing Tests
def test_multiple_files(mocker, tmp_path, capsys):
    """Test handling of multiple files via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    files = []
    for i in range(3):
        f = tmp_path / f"test{i}.txt"
        f.write_text(f"content{i}")
        files.append(str(f))
    
    main(['-m', 'llama2', 'test'] + files)
    
    # Verify all files were included in prompt
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    prompt = payload['prompt']
    assert all(f"content{i}" in prompt for i in range(3))

def test_special_characters(mocker, tmp_path, capsys):
    """Test handling of file paths with special characters via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    file_path = tmp_path / "test with spaces!@#$.txt"
    file_path.write_text("content")
    
    main(['-m', 'llama2', 'test', str(file_path)])
    
    # Verify the file was processed correctly
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'content' in payload['prompt']

def test_path_handling(mocker, tmp_path, capsys):
    """Test handling of relative vs absolute paths via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Test absolute path
    abs_file = tmp_path / "abs_test.txt"
    abs_file.write_text("abs content")
    main(['-m', 'llama2', 'test', str(abs_file)])
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'abs content' in payload['prompt']
    
    # Test relative path
    mock_post.reset_mock()
    with patch('os.getcwd', return_value=str(tmp_path)):
        rel_file = Path("rel_test.txt")
        (tmp_path / rel_file).write_text("rel content")
        main(['-m', 'llama2', 'test', str(rel_file)])
        assert mock_post.called
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert 'rel content' in payload['prompt']

# Remote Server Tests
def test_remote_connection(mocker, capsys):
    """Test connection to remote Ollama server via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    with patch.dict(os.environ, {'OLLAMA_HOST': 'http://test:11434'}):
        main(['test prompt'])
        
        # Verify endpoint URL uses OLLAMA_HOST
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://test:11434/api/generate'

def test_remote_connection_error(mocker, capsys):
    """Test error handling for connection issues via HTTP API."""
    import requests
    mock_post = mocker.patch('requests.post')
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    
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

def test_streaming_output(mocker, capsys):
    """Test that streaming output is emitted correctly via HTTP API."""
    # Create a response with multiple chunks
    chunks = ["Hello", " ", "world", "!"]
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response(chunks, done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    main(['-m', 'llama3.2', 'test'])
    
    # Verify output was streamed
    captured = capsys.readouterr()
    assert 'Hello world!' in captured.out
    
    # Verify API was called with stream=True
    call_args = mock_post.call_args
    assert call_args[1]['json']['stream'] is True

def test_no_images_in_text_only_request(mocker, capsys):
    """Test that images field is not included in text-only requests."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    main(['-m', 'llama3.2', 'test prompt'])
    
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'images' not in payload

def test_images_in_vision_request(mocker, tmp_path, capsys):
    """Test that images field is included in vision requests."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(b'fake_image_data')
    
    main(['-m', 'llava', 'describe', str(image_file)])
    
    call_args = mock_post.call_args
    payload = call_args[1]['json']
    assert 'images' in payload
    assert len(payload['images']) == 1
    assert isinstance(payload['images'][0], str)  # base64 encoded string

# Keep subprocess tests for ollama list and ollama show --modelfile
def test_save_modelfile_success(mocker, tmp_path, monkeypatch):
    """Test successful Modelfile save (still uses subprocess)."""
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
    """Test list_installed_models with JSON output (still uses subprocess)."""
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

def test_host_port_override_env(mocker, capsys):
    """Test that -h and -p flags override OLLAMA_HOST environment variable via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Clear any existing OLLAMA_HOST
    with patch.dict(os.environ, {}, clear=True):
        main(['-h', 'example.com', '-p', '1234', 'test'])
        
        # Verify endpoint URL uses the host/port flags
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://example.com:1234/api/generate'

def test_host_only_default_port(mocker, capsys):
    """Test that -h flag uses default port 11434 via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    with patch.dict(os.environ, {}, clear=True):
        main(['-h', 'example.com', 'test'])
        
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://example.com:11434/api/generate'

def test_port_only_default_host(mocker, capsys):
    """Test that -p flag uses default host localhost via HTTP API."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = create_mock_streaming_response("Response", done=True)
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    with patch.dict(os.environ, {}, clear=True):
        main(['-p', '12000', 'test'])
        
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://localhost:12000/api/generate'

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

def test_error_surfacing_config_load_failure(mocker, capsys, tmp_path, monkeypatch):
    """Test that config load errors are surfaced with warnings."""
    import yaml
    from ol.config import Config
    
    # Create a corrupted config file
    config_file = tmp_path / 'config.yaml'
    config_file.write_text('invalid: yaml: content: [')
    
    # Mock the config file path
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    
    # Test normal mode - should show concise warning
    config = Config(debug=False)
    captured = capsys.readouterr()
    assert 'Warning' in captured.err
    assert 'Failed to load config' in captured.err or 'config' in captured.err.lower()
    
    # Test debug mode - should show full exception
    config = Config(debug=True)
    captured = capsys.readouterr()
    assert 'Warning' in captured.err or 'Error' in captured.err
    # In debug mode, should have more detail

def test_error_surfacing_json_parse_failure(mocker, capsys):
    """Test that JSON parsing errors in streaming are surfaced."""
    mock_response = MagicMock()
    # Create response with invalid JSON
    mock_response.iter_lines.return_value = iter([
        b'{"response": "valid"}',
        b'invalid json line',
        b'{"response": "", "done": true}'
    ])
    mock_response.raise_for_status = MagicMock()
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    
    # Test normal mode
    main(['-m', 'llama3.2', 'test'])
    captured = capsys.readouterr()
    # Should still work but may show warnings
    
    # Test debug mode - should show JSON decode error details
    main(['-d', '-m', 'llama3.2', 'test'])
    captured = capsys.readouterr()
    # In debug mode, should show more detail about JSON errors

def test_error_surfacing_hostname_parse_failure(mocker, capsys, tmp_path, monkeypatch):
    """Test that hostname parsing errors are surfaced."""
    from ol.cli import get_hostname_for_filename
    
    # Test with invalid OLLAMA_HOST
    with patch.dict(os.environ, {'OLLAMA_HOST': 'invalid://url:with:too:many:colons'}):
        # Normal mode - should show concise warning
        hostname = get_hostname_for_filename(debug=False)
        captured = capsys.readouterr()
        assert 'Warning' in captured.err
        assert 'OLLAMA_HOST' in captured.err or 'hostname' in captured.err.lower()
        
        # Debug mode - should show full exception
        hostname = get_hostname_for_filename(debug=True)
        captured = capsys.readouterr()
        assert 'Warning' in captured.err
        # Should have more detail in debug mode

def test_error_surfacing_version_cache_failure(mocker, capsys, tmp_path, monkeypatch):
    """Test that version cache errors are surfaced."""
    from ol.version import VersionManager
    
    # Create a corrupted cache file
    cache_file = tmp_path / '.ol_version_cache.json'
    cache_file.write_text('invalid json{')
    
    # Mock the cache file path
    monkeypatch.setattr('ol.version.Path.home', lambda: tmp_path)
    
    # Test normal mode
    vm = VersionManager(debug=False)
    vm.version_cache = cache_file
    vm._load_cache()
    captured = capsys.readouterr()
    assert 'Warning' in captured.err
    
    # Test debug mode
    vm = VersionManager(debug=True)
    vm.version_cache = cache_file
    vm._load_cache()
    captured = capsys.readouterr()
    assert 'Warning' in captured.err
    # Should have more detail in debug mode
