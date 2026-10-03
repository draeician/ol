"""Tests for clipboard OCR (`ol --ocr`) and clipboard helpers."""

import base64
import json
import sys

import pytest
from unittest.mock import MagicMock

from PIL import Image

import ol.clipboard as clipboard
from ol.clipboard import ClipboardError
from ol.cli import main


@pytest.fixture(autouse=True)
def _isolate_runtime(mocker, tmp_path, monkeypatch):
    """Keep OCR tests hermetic: no real clipboard, config, or Ollama."""
    mocker.patch('ol.cli.ensure_prompt_fits_context')
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    monkeypatch.delenv('OLLAMA_HOST', raising=False)


def _config_mock(mocker, vision_model='llava', vision_host=None):
    config = mocker.Mock()
    config.get_model_for_type.return_value = vision_model
    config.get_host_for_type.return_value = vision_host
    config.get_temperature_for_type.return_value = 0.7
    config.set_last_used_model = mocker.Mock()
    return config


def _patch_ocr_transport(mocker, result='text', vision_model='llava', vision_host=None):
    config = _config_mock(mocker, vision_model=vision_model, vision_host=vision_host)
    mocker.patch('ol.cli.Config', return_value=config)
    mocker.patch(
        'ol.clipboard.get_clipboard_image_base64',
        return_value='ZmFrZV9pbWFnZQ==',
    )
    mocker.patch('ol.clipboard.set_clipboard_text')
    mock_api = mocker.patch('ol.cli.call_ollama_api', return_value=result)
    return config, mock_api


# --- Clipboard helper tests ---

def test_get_clipboard_image_base64_png(mocker):
    """grabclipboard() PIL image becomes PNG base64 with no temp file."""
    img = Image.new('RGB', (2, 2), 'white')
    mocker.patch.object(clipboard.ImageGrab, 'grabclipboard', return_value=img)
    mock_open = mocker.patch('builtins.open')

    result = clipboard.get_clipboard_image_base64()

    data = base64.b64decode(result)
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    mock_open.assert_not_called()


def test_get_clipboard_image_none_raises(mocker):
    """None clipboard content raises ClipboardError."""
    mocker.patch.object(clipboard.ImageGrab, 'grabclipboard', return_value=None)
    with pytest.raises(ClipboardError):
        clipboard.get_clipboard_image_base64()


def test_get_clipboard_image_filename_list_raises(mocker):
    """A filename-list clipboard result is rejected."""
    mocker.patch.object(
        clipboard.ImageGrab,
        'grabclipboard',
        return_value=['/tmp/screenshot.png'],
    )
    with pytest.raises(ClipboardError):
        clipboard.get_clipboard_image_base64()


def test_get_clipboard_image_backend_error(mocker):
    """Pillow backend errors become a useful ClipboardError."""
    mocker.patch.object(
        clipboard.ImageGrab,
        'grabclipboard',
        side_effect=OSError('clipboard unavailable'),
    )
    with pytest.raises(ClipboardError) as exc:
        clipboard.get_clipboard_image_base64()
    assert 'xclip' in str(exc.value)
    assert 'wl-clipboard' in str(exc.value)


def test_set_clipboard_text_calls_pyperclip(mocker):
    """set_clipboard_text copies the exact text via pyperclip."""
    mock_copy = mocker.patch('pyperclip.copy')
    clipboard.set_clipboard_text('hello world')
    mock_copy.assert_called_once_with('hello world')


def test_set_clipboard_text_failure(mocker):
    """pyperclip failures become ClipboardError."""
    mocker.patch('pyperclip.copy', side_effect=RuntimeError('no clipboard'))
    with pytest.raises(ClipboardError):
        clipboard.set_clipboard_text('hello')


# --- OCR orchestration tests ---

def test_ocr_default_routes_to_chat(mocker):
    """Default OCR uses the vision model and /api/chat with image_data."""
    config = _config_mock(mocker, vision_model='llava')
    mocker.patch('ol.cli.Config', return_value=config)
    mocker.patch(
        'ol.clipboard.get_clipboard_image_base64',
        return_value='ZmFrZV9pbWFnZQ==',
    )
    mocker.patch('ol.clipboard.set_clipboard_text')

    mock_response = MagicMock()
    mock_response.iter_lines.return_value = iter([
        json.dumps({
            'message': {'role': 'assistant', 'content': 'OCR text'},
            'done': False,
        }).encode('utf-8'),
        json.dumps({
            'message': {'role': 'assistant', 'content': ''},
            'done': True,
            'done_reason': 'stop',
        }).encode('utf-8'),
    ])
    mock_response.raise_for_status = MagicMock()
    mock_post = mocker.patch('requests.post', return_value=mock_response)

    main(['--ocr'])

    assert mock_post.call_args[0][0] == 'http://localhost:11434/api/chat'
    payload = mock_post.call_args[1]['json']
    assert payload['model'] == 'llava'
    assert payload['messages'][0]['images'] == ['ZmFrZV9pbWFnZQ==']
    assert payload['options']['temperature'] == 0.0
    assert payload['stream'] is True


def test_ocr_explicit_model_overrides(mocker):
    """-m overrides the configured vision model."""
    _, mock_api = _patch_ocr_transport(mocker)

    main(['--ocr', '-m', 'custom-vision'])

    assert mock_api.call_args[0][0] == 'custom-vision'


def test_ocr_explicit_temperature_overrides(mocker):
    """--temperature overrides the OCR default of 0.0."""
    _, mock_api = _patch_ocr_transport(mocker)

    main(['--ocr', '--temperature', '0.5'])

    assert mock_api.call_args[0][2] == 0.5


def test_ocr_default_temperature_is_zero(mocker):
    """Without --temperature, OCR uses 0.0."""
    _, mock_api = _patch_ocr_transport(mocker)

    main(['--ocr'])

    assert mock_api.call_args[0][2] == 0.0


def test_ocr_passes_image_data_and_echo_false(mocker):
    """OCR reuses the transport with image_data and echo=False."""
    _, mock_api = _patch_ocr_transport(mocker)

    main(['--ocr'])

    assert mock_api.call_args.kwargs['image_data'] == ['ZmFrZV9pbWFnZQ==']
    assert mock_api.call_args.kwargs['echo'] is False


def test_ocr_uses_configured_vision_host(mocker):
    """Configured vision host is used when no CLI/env host exists."""
    _, mock_api = _patch_ocr_transport(mocker, vision_host='http://vision:11434')

    main(['--ocr'])

    assert mock_api.call_args.kwargs['env']['OLLAMA_HOST'] == 'http://vision:11434'


def test_ocr_env_host_precedence_over_config(mocker, monkeypatch):
    """Existing OLLAMA_HOST beats the configured vision host."""
    _, mock_api = _patch_ocr_transport(mocker, vision_host='http://vision:11434')
    monkeypatch.setenv('OLLAMA_HOST', 'http://env:11434')

    main(['--ocr'])

    assert mock_api.call_args.kwargs['env']['OLLAMA_HOST'] == 'http://env:11434'


def test_ocr_cli_host_precedence(mocker, monkeypatch):
    """CLI -h/-p beats environment and configured host."""
    _, mock_api = _patch_ocr_transport(mocker, vision_host='http://vision:11434')
    monkeypatch.setenv('OLLAMA_HOST', 'http://env:11434')

    main(['--ocr', '-h', 'server', '-p', '1234'])

    assert mock_api.call_args.kwargs['env']['OLLAMA_HOST'] == 'http://server:1234'


def test_ocr_keep_sets_keep_alive(mocker):
    """--keep passes keep_alive=-1 to the transport."""
    _, mock_api = _patch_ocr_transport(mocker)

    main(['--ocr', '-k'])

    assert mock_api.call_args.kwargs['keep_alive'] == -1


def test_ocr_success_output_fidelity(mocker, capsys):
    """Successful OCR copies exact text and prints it with no decoration."""
    text = 'Line one\n  Line two\n'
    config, _ = _patch_ocr_transport(mocker, result=text)
    mock_set = mocker.patch('ol.clipboard.set_clipboard_text')

    main(['--ocr'])

    mock_set.assert_called_once_with(text)
    assert capsys.readouterr().out == text
    config.set_last_used_model.assert_called_once_with('llava')


def test_ocr_empty_result_no_clipboard_write(mocker, capsys):
    """Whitespace-only OCR is unsuccessful and leaves the clipboard alone."""
    config, _ = _patch_ocr_transport(mocker, result='   \n \t ')
    mock_set = mocker.patch('ol.clipboard.set_clipboard_text')

    with pytest.raises(SystemExit) as exc:
        main(['--ocr'])

    assert exc.value.code == 1
    mock_set.assert_not_called()
    assert 'no text' in capsys.readouterr().err


def test_ocr_clipboard_write_failure_keeps_stdout(mocker, capsys):
    """Clipboard write failure still emits the result to stdout."""
    text = 'recovered text'
    config, _ = _patch_ocr_transport(mocker, result=text)
    mocker.patch(
        'ol.clipboard.set_clipboard_text',
        side_effect=ClipboardError('write failed'),
    )

    with pytest.raises(SystemExit) as exc:
        main(['--ocr'])

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == text
    assert 'write failed' in captured.err
    config.set_last_used_model.assert_not_called()


def test_ocr_rejects_positional_prompt(mocker, capsys):
    """--ocr cannot be combined with a positional prompt."""
    with pytest.raises(SystemExit) as exc:
        main(['--ocr', 'a prompt'])
    assert exc.value.code == 1
    assert '--ocr' in capsys.readouterr().err


def test_ocr_rejects_positional_files(mocker, capsys):
    """--ocr cannot be combined with positional files."""
    with pytest.raises(SystemExit) as exc:
        main(['--ocr', 'image.png', 'notes.txt'])
    assert exc.value.code == 1
    assert '--ocr' in capsys.readouterr().err


def test_ocr_rejects_file_flag(mocker, capsys):
    """--ocr cannot be combined with -f/--file."""
    with pytest.raises(SystemExit) as exc:
        main(['--ocr', '-f', 'prompt.txt'])
    assert exc.value.code == 1
    assert '--ocr' in capsys.readouterr().err


def test_ocr_dispatch_before_stdin(mocker):
    """--ocr must not consume piped/redirected STDIN."""
    _patch_ocr_transport(mocker)

    stdin_mock = mocker.patch.object(sys, 'stdin')
    stdin_mock.isatty.return_value = False
    stdin_mock.read.side_effect = AssertionError('stdin read during OCR')

    main(['--ocr'])


def test_ocr_propagates_done_reason_length(mocker):
    """OCR must not swallow the transport's fail-closed length handling."""
    _patch_ocr_transport(mocker)
    mocker.patch('ol.cli.call_ollama_api', side_effect=SystemExit(1))

    with pytest.raises(SystemExit) as exc:
        main(['--ocr'])

    assert exc.value.code == 1
