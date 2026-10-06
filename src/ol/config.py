"""Configuration management for ol."""

import copy
import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse


DEFAULT_OLLAMA_PORT = 11434


def normalize_ollama_host(host: str, default_port: int = DEFAULT_OLLAMA_PORT) -> str:
    """
    Normalize an Ollama host URL for HTTP API use.

    Ensures a scheme (http:// by default) and a port. Ollama's CLI treats a
    missing port as 11434, but raw ``requests`` calls would otherwise hit
    port 80/443 and fail.

    Args:
        host: Host string (e.g. ``192.168.1.1``, ``server:11434``,
            ``http://server``, ``https://server:443``).
        default_port: Port to use when none is present in the URL.

    Returns:
        Normalized host URL with scheme and port, without a trailing slash.
    """
    host = host.strip().rstrip('/')
    if not host:
        raise ValueError("host must not be empty")

    # Only add a scheme when none is present. Do not rewrite exotic schemes
    # (keeps invalid test URLs and non-http hosts intact for error paths).
    if '://' not in host:
        host = f'http://{host}'

    parsed = urlparse(host)
    try:
        existing_port = parsed.port
    except ValueError:
        # Malformed netloc/port (e.g. too many colons) — leave unchanged.
        return host

    if existing_port is not None:
        return host

    # No explicit port: inject Ollama's default before any path/query.
    # Skip if netloc is empty or already ends with ':' (ambiguous/malformed).
    if not parsed.netloc or parsed.netloc.endswith(':'):
        return host

    # Only default the port for http(s) Ollama endpoints.
    if parsed.scheme not in ('http', 'https'):
        return host

    netloc = f'{parsed.netloc}:{default_port}'
    rebuilt = f'{parsed.scheme}://{netloc}'
    if parsed.path:
        rebuilt += parsed.path
    if parsed.query:
        rebuilt += f'?{parsed.query}'
    return rebuilt


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
        'decision': 'tev1',
        'decision_vision': 'clef-flash',
        'last_used': None
    },
    'hosts': {
        'text': None,
        'vision': None,
        'decision': None,
        'decision_vision': None
    },
    'temperature': {
        'text': 0.7,
        'vision': 0.7
    },
    'decisions': {
        'default_profiles': {
            'text': None,
            'vision': 'nsfw'
        }
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
        '.pdf': 'Please summarize or extract the key points from this PDF document:',
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
            # Create default config (deep copy so nested dicts are not shared)
            config = copy.deepcopy(DEFAULT_CONFIG)
            self._save_config(config)
            return config

        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
                # Deep merge with defaults to ensure all nested keys exist
                merged = deep_merge(copy.deepcopy(DEFAULT_CONFIG), config)
                return merged
        except Exception as e:
            if self.debug:
                import traceback
                print(f"Error loading config: {e}", file=os.sys.stderr)
                traceback.print_exc(file=os.sys.stderr)
            else:
                print(f"Warning: Failed to load config file, using defaults: {e}", file=os.sys.stderr)
            return copy.deepcopy(DEFAULT_CONFIG)

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
        if host:
            # Re-normalize on read so older configs without a port still work.
            host = normalize_ollama_host(host)
        if self.debug:
            print(f"DEBUG: get_host_for_type({type_}) -> {host}")
        return host

    def set_host_for_type(self, type_: str, host: str) -> None:
        """Set the host for a specific model type."""
        # Normalize host URL format (scheme + default Ollama port)
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

        Ensures scheme (http:// by default) and Ollama's default port (11434)
        when the caller omitted a port.

        Args:
            host: Host string (e.g., 'server:11434', 'http://server', 'localhost')

        Returns:
            Normalized host URL with protocol and port
        """
        return normalize_ollama_host(host)

    def get_model_and_host_for_type(self, type_: str = 'text') -> tuple[str, Optional[str]]:
        """Get both model name and host for the specified type."""
        model = self.get_model_for_type(type_)
        host = self.get_host_for_type(type_)
        if self.debug:
            print(f"DEBUG: get_model_and_host_for_type({type_}) -> ({model}, {host})")
        return model, host

    def get_default_decision_profile(self, category: str = 'text') -> Optional[str]:
        """
        Get the default decision profile for text or vision category.
        
        Args:
            category: 'text' or 'vision'
        
        Returns:
            Profile name or None
        """
        return self.config.get('decisions', {}).get('default_profiles', {}).get(category)

    def set_default_decision_profile(self, category: str, profile: Optional[str]) -> None:
        """
        Set the default decision profile for text or vision category.
        
        Args:
            category: 'text' or 'vision'
            profile: Profile name or None
        """
        if 'decisions' not in self.config:
            self.config['decisions'] = {}
        if 'default_profiles' not in self.config['decisions']:
            self.config['decisions']['default_profiles'] = {}
        
        self.config['decisions']['default_profiles'][category] = profile
        self._save_config(self.config) 