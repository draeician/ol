import pytest
from ol.cli import main
import subprocess

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
    mock_run.assert_called_once_with(['ollama', 'list'], check=True)

def test_run_with_model(mocker):
    """Test running with a specific model."""
    mock_run = mocker.patch('subprocess.run')
    main(['-m', 'codellama', 'test prompt'])
    mock_run.assert_called_once_with(
        ['ollama', 'run', 'codellama'],
        input=b'test prompt',
        check=True
    )

def test_debug_output(mocker, capsys, tmp_path):
    """Test debug output with file processing."""
    mock_run = mocker.patch('subprocess.run')
    
    # Create a temporary test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    main(['-d', '-m', 'llama3.2', 'test prompt', str(test_file)])
    
    captured = capsys.readouterr()
    debug_output = captured.out
    
    # Check debug information is present
    assert "=== Debug Information ===" in debug_output
    assert "Model: llama3.2" in debug_output
    assert "Base Prompt: test prompt" in debug_output
    assert "Added content from" in debug_output
    assert "=== Final Prompt ===" in debug_output
    assert "=== Sending to Ollama ===" in debug_output
    
    # Verify Ollama command was called
    mock_run.assert_called_once() 