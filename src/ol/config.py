"""Configuration management for ol."""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any


def deep_merge(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with overrides taking precedence.
    
    Recursively merges nested dictionaries, so that:
    - Missing nested keys remain populated from defaults
    - Explicit user overrides win deterministically
    
    Args:
        defaults: The default dictionary (base)
        overrides: The dictionary with overrides (takes precedence)
    
    Returns:
        A new dictionary with deep-merged values
    """
    result = defaults.copy()
    
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override with user value (or add new key)
            result[key] = value
    
    return result

DEFAULT_CONFIG = {
    'models': {
        'text': 'llama3.2',
        'vision': 'llama3.2-vision',
        'last_used': None
    },
    'hosts': {
        'text': None,
        'vision': None
    },
    'temperature': {
        'text': 0.7,
        'vision': 0.7
    },
    'default_prompts': {
        '.py': 'Review this Python code and provide suggestions for improvement:',
        '.js': 'Review this JavaScript code and provide suggestions for improvement:',
        '.md': 'Can you explain this markdown document?',
        '.txt': 'Can you analyze this text?',
        '.json': 'Can you explain this JSON data?',
        '.yaml': 'Can you explain this YAML configuration?',
        '.jpg': 'What do you see in this image?',
        '.png': 'What do you see in this image?',
        '.gif': 'What do you see in this image?',
        # Add more file types as needed
    }
}

class Config:
    """Configuration manager for ol."""

    def __init__(self, debug: bool = False):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / '.config' / 'ol'
        self.config_file = self.config_dir / 'config.yaml'
        self.debug = debug
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_file.exists():
            # Create default config
            config = DEFAULT_CONFIG.copy()
            self._save_config(config)
            return config

        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
                # Deep merge with defaults to ensure all nested keys exist
                merged = deep_merge(DEFAULT_CONFIG, config)
                return merged
        except Exception as e:
            if self.debug:
                import traceback
                print(f"Error loading config: {e}", file=os.sys.stderr)
                traceback.print_exc(file=os.sys.stderr)
            else:
                print(f"Warning: Failed to load config file, using defaults: {e}", file=os.sys.stderr)
            return DEFAULT_CONFIG.copy()

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        except Exception as e:
            if self.debug:
                import traceback
                print(f"Error saving config: {e}", file=os.sys.stderr)
                traceback.print_exc(file=os.sys.stderr)
            else:
                print(f"Warning: Failed to save config: {e}", file=os.sys.stderr)

    def get_model_for_type(self, type_: str = 'text') -> str:
        """Get the model for the specified type."""
        model = self.config['models'].get(type_, DEFAULT_CONFIG['models']['text'])
        if self.debug:
            print(f"DEBUG: get_model_for_type({type_}) -> {model}")
        return model

    def get_last_used_model(self) -> Optional[str]:
        """Get the last used model."""
        model = self.config['models'].get('last_used')
        if self.debug:
            print(f"DEBUG: get_last_used_model() -> {model}")
        return model

    def set_last_used_model(self, model: str) -> None:
        """Set the last used model."""
        if self.debug:
            print(f"DEBUG: set_last_used_model({model})")
        self.config['models']['last_used'] = model
        self._save_config(self.config)

    def get_default_prompt(self, file_path: str) -> Optional[str]:
        """Get the default prompt for a file type."""
        ext = Path(file_path).suffix.lower()
        return self.config['default_prompts'].get(ext)

    def set_default_prompt(self, extension: str, prompt: str) -> None:
        """Set the default prompt for a file type."""
        self.config['default_prompts'][extension] = prompt
        self._save_config(self.config)

    def set_model_for_type(self, type_: str, model: str) -> None:
        """Set the model for a specific type."""
        self.config['models'][type_] = model
        self._save_config(self.config)

    def get_temperature_for_type(self, type_: str = 'text') -> float:
        """Get the temperature for the specified type."""
        temp = self.config.get('temperature', {}).get(type_, DEFAULT_CONFIG['temperature'][type_])
        if self.debug:
            print(f"DEBUG: get_temperature_for_type({type_}) -> {temp}")
        return float(temp)

    def set_temperature_for_type(self, type_: str, temperature: float) -> None:
        """Set the temperature for a specific type."""
        # Validate temperature range
        if not (0.0 <= temperature <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
        
        # Ensure temperature section exists
        if 'temperature' not in self.config:
            self.config['temperature'] = {}
        
        self.config['temperature'][type_] = temperature
        self._save_config(self.config)

    def get_host_for_type(self, type_: str = 'text') -> Optional[str]:
        """Get the configured host for the specified model type."""
        host = self.config.get('hosts', {}).get(type_)
        if self.debug:
            print(f"DEBUG: get_host_for_type({type_}) -> {host}")
        return host

    def set_host_for_type(self, type_: str, host: str) -> None:
        """Set the host for a specific model type."""
        # Normalize host URL format
        normalized_host = self._normalize_host(host)
        
        # Ensure hosts section exists
        if 'hosts' not in self.config:
            self.config['hosts'] = {}
        
        self.config['hosts'][type_] = normalized_host
        if self.debug:
            print(f"DEBUG: set_host_for_type({type_}, {normalized_host})")
        self._save_config(self.config)

    def _normalize_host(self, host: str) -> str:
        """
        Normalize host URL format.
        
        Ensures host has http:// or https:// prefix.
        If host is just 'localhost' or 'localhost:port', adds http:// prefix.
        
        Args:
            host: Host string (e.g., 'server:11434', 'http://server:11434', 'localhost')
        
        Returns:
            Normalized host URL with protocol prefix
        """
        host = host.strip()
        
        # If already has protocol, return as-is
        if host.startswith('http://') or host.startswith('https://'):
            return host
        
        # Add http:// prefix
        return f'http://{host}'

    def get_model_and_host_for_type(self, type_: str = 'text') -> tuple[str, Optional[str]]:
        """Get both model name and host for the specified type."""
        model = self.get_model_for_type(type_)
        host = self.get_host_for_type(type_)
        if self.debug:
            print(f"DEBUG: get_model_and_host_for_type({type_}) -> ({model}, {host})")
        return model, host 