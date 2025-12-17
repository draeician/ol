# Ollama REPL Wrapper (ol)

A Python command-line utility that wraps the Ollama REPL, providing enhanced functionality and configuration options for both local and remote Ollama instances.

## Usage

```bash
# Local Usage
ol [options] "PROMPT" [FILES...]

# Remote Usage
OLLAMA_HOST=http://server:11434 ol [options] "PROMPT" [FILES...]
```

## Arguments
- `-l, --list`                    : List models (works with both local and remote instances)
- `-m MODEL, --model MODEL`       : Model to use for this REPL (default: from config)
- `-d, --debug`                   : Show debug information including API request details
- `-h HOST, --host HOST`          : Ollama host (default: localhost). Overrides OLLAMA_HOST for this command.
- `-p PORT, --port PORT`          : Ollama port (default: 11434). Overrides OLLAMA_HOST for this command.
- `--set-default-model TYPE MODEL`: Set default model for type (text or vision). Usage: `--set-default-model text codellama`
- `--set-default-temperature TYPE TEMP`: Set default temperature for type (text or vision). Usage: `--set-default-temperature text 0.8`
- `--temperature TEMP`             : Temperature for this command (0.0-2.0, overrides default)
- `--save-modelfile`               : Download and save the Modelfile for the specified model
- `-a, --all`                      : Save Modelfiles for all models (requires --save-modelfile)
- `--output-dir DIR`               : Output directory for saved Modelfile (default: current working directory)
- `--version`                      : Show version information
- `--check-updates`                : Check for available updates
- `--update`                       : Update to the latest version if available
- `--help, -?`                     : Show help message and exit
- `"PROMPT"`                       : The prompt to be used in the REPL instance (optional if files provided)
- `FILES`                          : File(s) to be injected into the prompt
                                    For remote vision models, absolute paths are required

**Note**: Running `ol` without any arguments displays the current configuration defaults (host, models, temperatures).

## Environment Variables
- `OLLAMA_HOST`    : URL of remote Ollama instance (e.g., http://server:11434)
                    Leave unset for local instance

## Features

### Core Functionality
- Command-line interface to Ollama
- Support for both local and remote Ollama instances via HTTP API
- File content injection into prompts
- Model selection and management
- Temperature control for text and vision models
- Debug output option showing API request details
- Automatic configuration initialization during installation
- Display current configuration defaults when run without arguments

### Configuration System
- YAML-based configuration at `~/.config/ol/config.yaml`
- Automatic initialization during package installation
- Directory structure:
  - `config.yaml`: Main configuration file
  - `history.yaml`: Command history
  - `templates/`: Custom templates directory
  - `cache/`: Cache directory for responses
- Default models for different content types:
  - Text: llama3.2
  - Vision: llama3.2-vision
- Default temperature settings for text and vision models (default: 0.7 for both)
- Temperature control via CLI (per-command override or default configuration)
- Last used model tracking
- Default prompts by file extension
- Automatic model selection based on file type

### File Handling
- Multiple file support
- Default prompts for common file types:
  - Python (.py)
  - JavaScript (.js)
  - Markdown (.md)
  - Text (.txt)
  - JSON (.json)
  - YAML (.yaml)
  - Images (.jpg, .png, .gif)
- Special handling for remote vision models

## Installation

```bash
# Using pipx (recommended)
pipx install .
or from the git repo directly
pipx install git+https://github.com/draeician/ol


# Using pip
pip install . or pipx uninstall ol
```

## Planned Enhancements

### System Prompts and Templates
- Pre-defined system prompts for different tasks
- Custom prompt templates with variables
- Template categories (code review, documentation, analysis)
- User-defined template management
- Template sharing and import/export

### Command History
- Store command history in `~/.config/ol/history.yaml`
- Search through previous prompts
- Reuse successful prompts
- Session management
- Favorite/bookmark useful prompts

### Model-Specific Parameters
- Temperature control (implemented):
  - Default temperature per model type (text/vision)
  - Per-command temperature override
  - Configuration via CLI or config file
- Planned enhancements:
  - Top-p
  - Max tokens
  - Context window size
  - Stop sequences
  - Model aliases and groups
  - Model-specific system prompts

### Context Window Management
- Smart context windowing for large files
- Chunk management for long conversations
- File splitting strategies
- Context preservation between calls
- Token counting and optimization

### Multiple File Handling Improvements
- Directory support with glob patterns
- File type grouping
- Recursive file processing
- File content preprocessing
- Custom file type handlers

### Conversation Management
- Conversation history tracking
- Context continuation between prompts
- Conversation export/import
- Thread management
- Conversation summarization

### Output Processing
- Output formatting options
- Code block extraction
- Markdown rendering
- Syntax highlighting
- Export to various formats

### Integration Features
- Git integration for code review
- Editor integration
- API mode for programmatic access
- Webhook support
- Pipeline integration

### Performance Optimizations
- Caching mechanisms
- Parallel file processing
- Streaming responses
- Memory management
- Response compression

## Usage Examples

```bash
# Basic usage
ol "Your prompt" file.txt

# With model selection
ol -m codellama "Review this code" main.py

# Debug mode (shows API request details)
ol -d "Analyze this" data.json

# Using default prompts
ol main.py  # Uses Python code review template

# Multiple files
ol "Compare these" file1.py file2.py

# Image analysis
ol image.jpg  # Uses vision model automatically

# View current configuration defaults
ol

# Set default text model
ol --set-default-model text codellama

# Set default vision model
ol --set-default-model vision llava

# Set default temperature for text models
ol --set-default-temperature text 0.8

# Set default temperature for vision models
ol --set-default-temperature vision 0.5

# Use custom temperature for a single command
ol --temperature 0.9 "Your prompt here"

# Version management
ol --version
ol --check-updates
ol --update
```

## Command-Line Interface

```bash
ol [options] [prompt] [files...]

Options:
  -l, --list                      List available models
  -m, --model MODEL               Model to use (default: from config)
  -d, --debug                     Show debug information including API request details
  -h, --host HOST                 Ollama host (default: localhost)
  -p, --port PORT                 Ollama port (default: 11434)
  --set-default-model TYPE MODEL  Set default model for type (text or vision)
  --set-default-temperature TYPE TEMP  Set default temperature for type (text or vision)
  --temperature TEMP              Temperature for this command (0.0-2.0)
  --save-modelfile                Download and save the Modelfile for the specified model
  -a, --all                       Save Modelfiles for all models (requires --save-modelfile)
  --output-dir DIR                 Output directory for saved Modelfile
  --version                       Show version information
  --check-updates                 Check for available updates
  --update                        Update to the latest version if available
  --help, -?                      Show help message
```

**Note**: Running `ol` without any arguments displays the current configuration defaults.

## Configuration Structure

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

## Future Considerations

1. Plugin System
   - Custom handlers
   - User extensions
   - Community plugins

2. Security Features
   - Content filtering
   - Token management
   - Access control

3. Collaborative Features
   - Shared configurations
   - Team templates
   - Review workflows

4. Analytics
   - Usage statistics
   - Performance metrics
   - Cost tracking

5. Cloud Integration
   - Configuration sync
   - Backup/restore
   - Cross-device history
