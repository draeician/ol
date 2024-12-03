# ol - Ollama REPL Wrapper

A Python command-line wrapper for the Ollama REPL that supports both local and remote Ollama instances.

## Prerequisites

- Python 3.6 or higher
- Ollama installed (locally or on a remote server)
- pipx (recommended for installation)

## Installation

### Using pipx (Recommended)

```bash
# Install pipx if you haven't already
python -m pip install --user pipx
python -m pipx ensurepath

# Install ol
pipx install .
```

During installation, `ol` will automatically:
1. Create the configuration directory at `~/.config/ol/`
2. Initialize default configuration in `~/.config/ol/config.yaml`
3. Set up command history tracking in `~/.config/ol/history.yaml`
4. Create directories for templates and cache

### Using pip (Alternative)

```bash
pip install .
```

For development:

```bash
pip install -e .
```

## Remote Usage

You can use `ol` with a remote Ollama instance by setting the `OLLAMA_HOST` environment variable:

```bash
# Basic text prompt with remote instance
OLLAMA_HOST=http://server:11434 ol "What is the meaning of life?"

# Code review with specific model
OLLAMA_HOST=http://server:11434 ol -m codellama "Review this code" file.py

# Vision model with remote instance (requires absolute path)
OLLAMA_HOST=http://server:11434 ol "What's in this image?" /absolute/path/to/image.jpg

# List available models on remote instance
OLLAMA_HOST=http://server:11434 ol -l

# Debug mode shows exact commands
OLLAMA_HOST=http://server:11434 ol -d "Your prompt here"
```

### Remote Vision Models
When using vision models with a remote Ollama instance:
- Use absolute paths for image files
- Ensure the remote server has access to the image path
- The image path will be included in the prompt

## Local Usage

For local Ollama instances, simply run commands without the `OLLAMA_HOST` variable:

```bash
# List available models
ol -l

# Use a specific model
ol -m llama3.2 "Your prompt here"

# Include file contents in the prompt
ol "Your prompt here" file1.txt file2.txt

# Use a different model with files
ol -m codellama "Review this code" main.py test.py

# Show debug information
ol -d "Your prompt here" file1.txt

# Use default prompt based on file type
ol main.py  # Will use the default Python code review prompt
```

## Arguments

- `-l, --list`: List available models (works with both local and remote instances)
- `-m MODEL, --model MODEL`: Specify the model to use (default: from config)
- `-d, --debug`: Show debug information including equivalent shell commands
- `"PROMPT"`: The prompt to send to Ollama (optional if files are provided)
- `FILES`: Optional files to inject into the prompt

## Configuration

The tool uses a YAML configuration file located at `~/.config/ol/config.yaml`. This file is created automatically during installation with default settings.

### Directory Structure

```
~/.config/ol/
├── config.yaml     # Main configuration file
├── history.yaml    # Command history
├── templates/      # Custom templates directory
└── cache/         # Cache directory for responses
```

### Configuration Structure

```yaml
models:
  text: llama3.2      # Default model for text
  vision: llava       # Default model for images
  last_used: null     # Last used model (updated automatically)

default_prompts:
  .py: 'Review this Python code and provide suggestions for improvement:'
  .js: 'Review this JavaScript code and provide suggestions for improvement:'
  .md: 'Can you explain this markdown document?'
  .txt: 'Can you analyze this text?'
  .json: 'Can you explain this JSON data?'
  .yaml: 'Can you explain this YAML configuration?'
  .jpg: 'What do you see in this image?'
  .png: 'What do you see in this image?'
  .gif: 'What do you see in this image?'
```

## Examples

### Text Processing

```bash
# Local instance
ol "Explain this code" main.py
ol -m codellama "Review for security issues" *.py

# Remote instance
OLLAMA_HOST=http://server:11434 ol "Explain this code" main.py
OLLAMA_HOST=http://server:11434 ol -m codellama "Review for security issues" *.py
```

### Image Analysis

```bash
# Local instance
ol "What's in this image?" image.jpg

# Remote instance (requires absolute path)
OLLAMA_HOST=http://server:11434 ol "What's in this image?" /home/user/images/photo.jpg
```

### Debug Mode

```bash
# Show equivalent shell commands
ol -d "Your prompt" file.txt

# Debug with remote instance
OLLAMA_HOST=http://server:11434 ol -d "Your prompt" file.txt
```

## Configuration Management

You can manually edit the configuration files in `~/.config/ol/`:
- `config.yaml`: Main configuration file
- `history.yaml`: Command history
- `templates/`: Directory for custom templates
- `cache/`: Cache directory for responses

The configuration is automatically loaded and saved as you use the tool.

## Uninstallation

To uninstall the package:
```bash
pipx uninstall ol
```

To also remove configuration files:
```bash
rm -rf ~/.config/ol
``` 