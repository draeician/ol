import pytest
import yaml
import tempfile
from pathlib import Path
from ol.config import Config, deep_merge, DEFAULT_CONFIG


def test_deep_merge_preserves_nested_defaults():
    """Test that missing nested keys remain populated from defaults."""
    defaults = {
        'models': {
            'text': 'llama3.2',
            'vision': 'llama3.2-vision',
            'last_used': None
        },
        'temperature': {
            'text': 0.7,
            'vision': 0.7
        }
    }
    
    overrides = {
        'models': {
            'text': 'custom-model'  # Only override text, vision should remain
        }
    }
    
    result = deep_merge(defaults, overrides)
    
    # Explicit override should win
    assert result['models']['text'] == 'custom-model'
    # Missing nested key should remain from defaults
    assert result['models']['vision'] == 'llama3.2-vision'
    assert result['models']['last_used'] is None
    # Temperature section should remain intact
    assert result['temperature']['text'] == 0.7
    assert result['temperature']['vision'] == 0.7


def test_deep_merge_user_overrides_win():
    """Test that explicit user overrides win deterministically."""
    defaults = {
        'models': {
            'text': 'llama3.2',
            'vision': 'llama3.2-vision'
        },
        'temperature': {
            'text': 0.7,
            'vision': 0.7
        }
    }
    
    overrides = {
        'models': {
            'text': 'custom-text',
            'vision': 'custom-vision'
        },
        'temperature': {
            'text': 0.9
        }
    }
    
    result = deep_merge(defaults, overrides)
    
    # All explicit overrides should win
    assert result['models']['text'] == 'custom-text'
    assert result['models']['vision'] == 'custom-vision'
    assert result['temperature']['text'] == 0.9
    # vision temperature should remain from defaults
    assert result['temperature']['vision'] == 0.7


def test_deep_merge_multiple_nested_levels():
    """Test deep merge with multiple levels of nesting."""
    defaults = {
        'level1': {
            'level2': {
                'level3': 'default-value',
                'other': 'other-default'
            },
            'sibling': 'sibling-default'
        }
    }
    
    overrides = {
        'level1': {
            'level2': {
                'level3': 'override-value'
            }
        }
    }
    
    result = deep_merge(defaults, overrides)
    
    # Override should win
    assert result['level1']['level2']['level3'] == 'override-value'
    # Missing nested keys should remain
    assert result['level1']['level2']['other'] == 'other-default'
    assert result['level1']['sibling'] == 'sibling-default'


def test_deep_merge_adds_new_keys():
    """Test that new keys from overrides are added."""
    defaults = {
        'existing': {
            'key': 'value'
        }
    }
    
    overrides = {
        'existing': {
            'key': 'value',
            'new_key': 'new_value'
        },
        'new_section': {
            'new_key': 'new_value'
        }
    }
    
    result = deep_merge(defaults, overrides)
    
    # New keys should be added
    assert result['existing']['new_key'] == 'new_value'
    assert result['new_section']['new_key'] == 'new_value'


def test_config_load_preserves_nested_defaults(tmp_path, monkeypatch):
    """Test that Config._load_config preserves nested defaults when user config is partial."""
    # Mock the config directory
    config_dir = tmp_path / '.config' / 'ol'
    config_dir.mkdir(parents=True)
    config_file = config_dir / 'config.yaml'
    
    # Create a partial config that only overrides one nested value
    partial_config = {
        'models': {
            'text': 'custom-model'
            # Note: vision and last_used are missing
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.safe_dump(partial_config, f)
    
    # Mock Path.home to return our tmp_path
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    
    config = Config()
    
    # Explicit override should win
    assert config.get_model_for_type('text') == 'custom-model'
    # Missing nested key should remain from defaults
    assert config.get_model_for_type('vision') == 'llama3.2-vision'
    # Temperature defaults should remain intact
    assert config.get_temperature_for_type('text') == 0.7
    assert config.get_temperature_for_type('vision') == 0.7


def test_config_load_user_overrides_win(tmp_path, monkeypatch):
    """Test that explicit user overrides win deterministically."""
    config_dir = tmp_path / '.config' / 'ol'
    config_dir.mkdir(parents=True)
    config_file = config_dir / 'config.yaml'
    
    # Create a config with explicit overrides
    user_config = {
        'models': {
            'text': 'custom-text',
            'vision': 'custom-vision'
        },
        'temperature': {
            'text': 0.9,
            'vision': 0.5
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.safe_dump(user_config, f)
    
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    
    config = Config()
    
    # All explicit overrides should win
    assert config.get_model_for_type('text') == 'custom-text'
    assert config.get_model_for_type('vision') == 'custom-vision'
    assert config.get_temperature_for_type('text') == 0.9
    assert config.get_temperature_for_type('vision') == 0.5


def test_config_load_empty_config_uses_all_defaults(tmp_path, monkeypatch):
    """Test that empty config file uses all defaults."""
    config_dir = tmp_path / '.config' / 'ol'
    config_dir.mkdir(parents=True)
    config_file = config_dir / 'config.yaml'
    
    # Create empty config
    with open(config_file, 'w') as f:
        yaml.safe_dump({}, f)
    
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    
    config = Config()
    
    # All values should come from defaults
    assert config.get_model_for_type('text') == DEFAULT_CONFIG['models']['text']
    assert config.get_model_for_type('vision') == DEFAULT_CONFIG['models']['vision']
    assert config.get_temperature_for_type('text') == DEFAULT_CONFIG['temperature']['text']
    assert config.get_temperature_for_type('vision') == DEFAULT_CONFIG['temperature']['vision']


def test_deep_merge_non_dict_values():
    """Test that non-dict values are replaced (not merged)."""
    defaults = {
        'string_key': 'default',
        'number_key': 42,
        'nested': {
            'key': 'value'
        }
    }
    
    overrides = {
        'string_key': 'override',
        'number_key': 100,
        'nested': 'replaced'  # Replacing dict with string
    }
    
    result = deep_merge(defaults, overrides)
    
    # Non-dict values should be replaced
    assert result['string_key'] == 'override'
    assert result['number_key'] == 100
    assert result['nested'] == 'replaced'  # Dict replaced with string


def test_get_host_for_type_defaults_to_none(tmp_path, monkeypatch):
    """Test that get_host_for_type returns None by default."""
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    config = Config()
    assert config.get_host_for_type('text') is None
    assert config.get_host_for_type('vision') is None


def test_set_host_for_type(tmp_path, monkeypatch):
    """Test that host can be set and retrieved."""
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    config = Config()
    config.set_host_for_type('text', 'http://server:11434')
    assert config.get_host_for_type('text') == 'http://server:11434'
    
    config.set_host_for_type('vision', 'http://remote-server:11434')
    assert config.get_host_for_type('vision') == 'http://remote-server:11434'


def test_host_normalization(tmp_path, monkeypatch):
    """Test that hosts are normalized (http:// prefix added if missing)."""
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    config = Config()
    
    # Test without http:// prefix
    config.set_host_for_type('text', 'server:11434')
    assert config.get_host_for_type('text') == 'http://server:11434'
    
    # Test with http:// prefix (should remain unchanged)
    config.set_host_for_type('vision', 'http://remote:11434')
    assert config.get_host_for_type('vision') == 'http://remote:11434'
    
    # Test with https:// prefix (should remain unchanged)
    config.set_host_for_type('text', 'https://secure-server:11434')
    assert config.get_host_for_type('text') == 'https://secure-server:11434'
    
    # Test localhost without port
    config.set_host_for_type('vision', 'localhost')
    assert config.get_host_for_type('vision') == 'http://localhost'


def test_get_model_and_host_for_type(tmp_path, monkeypatch):
    """Test that get_model_and_host_for_type returns both model and host."""
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    config = Config()
    
    # Test without host configured
    model, host = config.get_model_and_host_for_type('text')
    assert model == 'llama3.2'
    assert host is None
    
    # Test with host configured
    config.set_host_for_type('text', 'http://server:11434')
    model, host = config.get_model_and_host_for_type('text')
    assert model == 'llama3.2'
    assert host == 'http://server:11434'


def test_config_load_preserves_hosts(tmp_path, monkeypatch):
    """Test that hosts persist in config file."""
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    config = Config()
    config.set_host_for_type('text', 'http://server:11434')
    config.set_host_for_type('vision', 'http://remote:11434')
    
    # Create new config instance to verify persistence
    config2 = Config()
    assert config2.get_host_for_type('text') == 'http://server:11434'
    assert config2.get_host_for_type('vision') == 'http://remote:11434'


def test_deep_merge_hosts(tmp_path, monkeypatch):
    """Test that deep merge works for hosts section."""
    monkeypatch.setattr('ol.config.Path.home', lambda: tmp_path)
    
    # Create config with partial hosts
    config_file = tmp_path / '.config' / 'ol' / 'config.yaml'
    config_file.parent.mkdir(parents=True)
    partial_config = {
        'hosts': {
            'text': 'http://text-server:11434'
            # vision not specified
        }
    }
    with open(config_file, 'w') as f:
        yaml.safe_dump(partial_config, f)
    
    config = Config()
    # Text host should be from user config
    assert config.get_host_for_type('text') == 'http://text-server:11434'
    # Vision host should default to None
    assert config.get_host_for_type('vision') is None

