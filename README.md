# ol - Ollama REPL Wrapper

A Python command-line wrapper for the Ollama REPL that supports both local and remote Ollama instances.

## Prerequisites

- Python 3.7 or higher
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

On first use, `ol` will automatically:
1. Create the configuration directory at `~/.config/ol/`
2. Initialize default configuration in `~/.config/ol/config.yaml`
3. Set up command history tracking in `~/.config/ol/history.yaml`
4. Create directories for templates and cache

**Note**: Initialization happens when you first run the `ol` command, not during installation. This ensures the package can be imported without side effects.

### Using pip (Alternative)

```bash
pip install .
```

For development:

```bash
pip install -e .
```

## Remote Usage

You can use `ol` with a remote Ollama instance by setting the `OLLAMA_HOST` environment variable or using the `-h/--host` and `-p/--port` flags:

```bash
# Basic text prompt with remote instance (using environment variable)
OLLAMA_HOST=http://server:11434 ol "What is the meaning of life?"

# Using CLI flags (overrides OLLAMA_HOST for this command)
ol -h server -p 11434 "What is the meaning of life?"

# Code review with specific model
OLLAMA_HOST=http://server:11434 ol -m codellama "Review this code" file.py
ol -h server -p 11434 -m codellama "Review this code" file.py

# Local custom port
ol -h localhost -p 11435 -m llama3.2 "Hello"

# Remote with custom port
ol -h api.myhost.com -p 11434 -m codellama "Review this" file.py

# Vision model with remote instance (requires absolute path)
OLLAMA_HOST=http://server:11434 ol "What's in this image?" /absolute/path/to/image.jpg

# List available models on remote instance
OLLAMA_HOST=http://server:11434 ol -l
ol -h server -p 11434 -l

# Debug mode shows exact commands
OLLAMA_HOST=http://server:11434 ol -d "Your prompt here"

# Save Modelfile from remote instance
OLLAMA_HOST=http://server:11434 ol -m llama3.2 --save-modelfile
```

### Remote Vision Models
When using vision models with a remote Ollama instance:
- Use absolute paths for image files
- Images are base64-encoded and sent in the API payload via the `/api/chat` endpoint
- The image data is transmitted directly to the remote Ollama API, not as file paths
- Vision and mixed-content requests automatically use the `/api/chat` endpoint, while text-only requests use `/api/generate`

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

# Save a model's Modelfile
ol -m llama3.2 --save-modelfile

# Save Modelfile to custom directory
ol -m llama3.2:latest --save-modelfile --output-dir ~/.config/ol/templates
```

## Arguments

- `-l, --list`: List available models (works with both local and remote instances)
- `-m MODEL, --model MODEL`: Specify the model to use (default: from config)
- `-d, --debug`: Show debug information including API request details
- `-h HOST, --host HOST`: Ollama host (default: localhost). Overrides OLLAMA_HOST for this command.
- `-p PORT, --port PORT`: Ollama port (default: 11434). Overrides OLLAMA_HOST for this command.
- `--set-default-model TYPE MODEL`: Set default model for type (text or vision). Usage: `--set-default-model text codellama`
- `--set-default-temperature TYPE TEMP`: Set default temperature for type (text or vision). Usage: `--set-default-temperature text 0.8`
- `--temperature TEMP`: Temperature for this command (0.0-2.0, overrides default)
- `--save-modelfile`: Download and save the Modelfile for the specified model
- `-a, --all`: Save Modelfiles for all models (requires --save-modelfile)
- `--output-dir DIR`: Output directory for saved Modelfile (default: current working directory)
- `--version`: Show version information
- `--check-updates`: Check for available updates
- `--update`: Update to the latest version if available
- `--help, -?`: Show help message and exit
- `"PROMPT"`: The prompt to send to Ollama (optional if files or STDIN are provided)
- `FILES`: Optional files to inject into the prompt

**Note**: 
- Running `ol` without any arguments displays the current configuration defaults (host, models, temperatures).
- You can pipe input to `ol` using `|` or redirect files using `<`. STDIN input is automatically used as the prompt.

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
  text: llama3.2          # Default model for text
  vision: llama3.2-vision  # Default model for images
  last_used: null          # Last used model (updated automatically)

temperature:
  text: 0.7    # Default temperature for text models (0.0-2.0)
  vision: 0.7  # Default temperature for vision models (0.0-2.0)

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

## Saving Modelfiles

You can download and save a model's Modelfile using the `--save-modelfile` flag:

```bash
# Save Modelfile to current directory
ol -m llama3.2 --save-modelfile

# Save Modelfile with tag (colons replaced with underscores in filename)
ol -m llama3.2:latest --save-modelfile

# Save to custom directory
ol -m llama3.2 --save-modelfile --output-dir ~/.config/ol/templates

# Save from remote instance
OLLAMA_HOST=http://server:11434 ol -m llama3.2 --save-modelfile

# Save Modelfiles for ALL models
ol --save-modelfile --all

# Save all Modelfiles to custom directory
ol --save-modelfile --all --output-dir ~/.config/ol/templates

# Save all Modelfiles from remote instance
OLLAMA_HOST=http://server:11434 ol --save-modelfile --all
```

The saved Modelfile will be named using the pattern: `<modelname>-<hostname>-<YYYYMMDD-HHMMSS>.modelfile`

- Model names are sanitized for filesystem safety: path-hostile characters (`/`, `\`, `:`, spaces, etc.) are replaced with underscores
- The hostname is automatically detected from your system
- Timestamp is in local time format `YYYYMMDD-HHMMSS`
- When using `--all`, each model's Modelfile is saved with its own timestamp
- If a model fails to save (e.g., due to filesystem issues), the process continues with remaining models

## Examples

### Text Processing

```bash
# Local instance
ol "Explain this code" main.py
ol -m codellama "Review for security issues" *.py

# Remote instance (using environment variable)
OLLAMA_HOST=http://server:11434 ol "Explain this code" main.py
OLLAMA_HOST=http://server:11434 ol -m codellama "Review for security issues" *.py

# Remote instance (using CLI flags)
ol -h server -p 11434 "Explain this code" main.py
ol -h server -p 11434 -m codellama "Review for security issues" *.py

# Local custom port
ol -h localhost -p 11435 -m llama3.2 "Hello"
```

### STDIN Input (Piping and Redirection)

You can pipe input or redirect files to `ol`:

```bash
# Pipe text input
echo "What is Python?" | ol

# Redirect file content
ol < file.txt

# Combine STDIN with prompt argument
echo "def hello():" | ol "Review this code"

# Pipe with files
cat code.py | ol main.py

# Pipe with remote instance
echo "Explain this" | OLLAMA_HOST=http://server:11434 ol

# Pipe with model selection
echo "Review this code" | ol -m codellama

# Multiline input via pipe
cat <<EOF | ol "Analyze this code"
def example():
    return True
EOF
```

**Note**: When STDIN is available (piping/redirection), it's automatically used as the prompt. If both STDIN and a prompt argument are provided, STDIN is combined with the prompt argument.

### Image Analysis

```bash
# Local instance
ol "What's in this image?" image.jpg

# Remote instance (requires absolute path)
OLLAMA_HOST=http://server:11434 ol "What's in this image?" /home/user/images/photo.jpg
```

### Debug Mode

```bash
# Show API request details and debug information
ol -d "Your prompt" file.txt

# Debug with remote instance
OLLAMA_HOST=http://server:11434 ol -d "Your prompt" file.txt
```

### Viewing Current Configuration

```bash
# Display current defaults (host, models, temperatures)
ol
```

### Configuration Management

You can set default models and temperatures using CLI commands:

```bash
# Set default text model
ol --set-default-model text codellama

# Set default vision model
ol --set-default-model vision llava

# Set default text temperature
ol --set-default-temperature text 0.8

# Set default vision temperature
ol --set-default-temperature vision 0.5
```

Or manually edit the configuration files in `~/.config/ol/`:
- `config.yaml`: Main configuration file
- `history.yaml`: Command history
- `templates/`: Directory for custom templates
- `cache/`: Cache directory for responses

The configuration is automatically loaded and saved as you use the tool.

### Temperature Control

```bash
# Use custom temperature for a single command (overrides default)
ol --temperature 0.9 "Your prompt here"

# Use lower temperature for more focused responses
ol --temperature 0.3 "Explain this code" main.py

# Temperature works with both text and vision models
ol --temperature 0.8 "What's in this image?" photo.jpg
```

### Version Management

```bash
# Check current version
ol --version

# Check for available updates
ol --check-updates

# Update to latest version
ol --update
```

## Uninstallation

To uninstall the package:
```bash
pipx uninstall ol
```

To also remove configuration files:
```bash
rm -rf ~/.config/ol
``` 