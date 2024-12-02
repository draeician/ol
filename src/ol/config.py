"""Configuration management for ol."""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any

DEFAULT_CONFIG = {
    'models': {
        'text': 'llama3.2',
        'vision': 'llava',
        'last_used': None
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

    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / '.config' / 'ol'
        self.config_file = self.config_dir / 'config.yaml'
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
                # Merge with defaults to ensure all keys exist
                merged = DEFAULT_CONFIG.copy()
                merged.update(config)
                return merged
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.", file=os.sys.stderr)
            return DEFAULT_CONFIG.copy()

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}", file=os.sys.stderr)

    def get_model_for_type(self, type_: str = 'text') -> str:
        """Get the model for the specified type."""
        return self.config['models'].get(type_, DEFAULT_CONFIG['models']['text'])

    def get_last_used_model(self) -> Optional[str]:
        """Get the last used model."""
        return self.config['models'].get('last_used')

    def set_last_used_model(self, model: str) -> None:
        """Set the last used model."""
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