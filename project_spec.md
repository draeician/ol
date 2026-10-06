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
- `--ps, --loaded`                : List models currently loaded in memory on the Ollama endpoint
- `-m MODEL, --model MODEL`       : Model to use for this REPL (default: from config)
- `-d, --debug`                   : Show debug information including API request details
- `-s, --stats`                   : Show performance metrics after the response (Ollama --verbose style)
- `-k, --keep`                    : Keep the model loaded forever after this request (keep_alive=-1)
- `-u, --unload`                  : Unload a model from memory (uses -m or default text model)
- `--ocr`                         : OCR an image from the clipboard and replace the clipboard with the extracted text
- `-f PROMPTFILE, --file PROMPTFILE`: Read prompt text from a file (mutually exclusive with a positional prompt)
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

## Shell Tab Completion

Enable once after install (bash or zsh):

```bash
# bash — add to ~/.bashrc
eval "$(register-python-argcomplete ol)"

# zsh — add to ~/.zshrc (after compinit)
eval "$(register-python-argcomplete ol)"
```

Completion covers filesystem paths for `-f`/`--file`, `--output-dir`, and positional content files; model names for `-m`; and `text`/`vision` for `--set-default-*` type arguments.

## Environment Variables
- `OLLAMA_HOST`    : URL of remote Ollama instance (e.g., http://server:11434)
                    Leave unset for local instance

## Features

### Core Functionality
- Command-line interface to Ollama
- Shell tab completion via argcomplete (bash/zsh) for path and model arguments
- Support for both local and remote Ollama instances via HTTP API
- File content injection into prompts
- Model selection and management
- Temperature control for text and vision models
- Debug output option showing API request details
- `-s`/`--stats` performance metrics (Ollama `--verbose` style) after responses
- `-k`/`--keep` to keep a model loaded forever after a request (`keep_alive=-1`)
- `-u`/`--unload` to unload a model from memory (`keep_alive=0`)
- `--ps`/`--loaded` to list models currently loaded via `/api/ps`
- `--ocr` to OCR an image from the system clipboard (input: clipboard image;
  output: stdout + clipboard text) using the configured vision model by default
  and an OCR default temperature of `0.0`; `-m`/`-h`/`-p`/`--temperature`
  override normal defaults
- Always-on context-window failsafe: refuses requests that cannot fit the
  effective model context (loaded `/api/ps` context when available, else
  `/api/show` maximum), and exits non-zero if the stream ends with
  `done_reason=length` (empty or truncated / compromised output)
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
  - PDFs (.pdf) with text extraction via `pypdf`
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

### System One decision mode (planned, not implemented)

The revised feature contract is [PLAN-systemone.md](PLAN-systemone.md), dated
2026-10-06. It supersedes the earlier Nimble/profile-only decision proposal;
older continuity notes are historical, not alternative specifications. The
current CLI reference elsewhere in this file still describes implemented
behavior. Do not advertise the following commands as available before delivery.

- Keep ordinary `text`/`vision` models unchanged. Add independent `decision`
  (default `tev1`) and `decision_vision` (default `clef-flash`) model/host
  categories. Any image, even alongside text, requires a vision-capable decision
  model. Validate capabilities; never drop evidence or silently switch models.
- Store default tasks independently: `decisions.default_profiles.text: null`
  and `decisions.default_profiles.vision: nsfw`. `ol -dc ./photo.jpg` runs the
  configured image task; `ol -dc nsfw ./photo.jpg` selects it explicitly.
- Explicit aliases are `-dc`, `--dc`, and `--decision`; preserve `-d` debugging.
  Support inline boolean questions before or after an image. Counting and other
  typed tasks use profiles/`--questions`, not invented answer ranges or chat.
  `ol -dc eggs ./eggs.jpg` uses a choice profile with 0-12, 13+, and unclear.
- Use versioned user-overridable profiles with input requirements, optional model,
  fallback state, API questions, and local result rules. Bundle editable `nsfw`
  and `eggs` starters. NSFW policy and review thresholds are illustrative, not
  calibrated guarantees. Errors are not negative classifications.
- Add explicit clipboard input (`-c`, leaving the clipboard unchanged), offline
  profile list/edit, completion, sequential `--each`, and stable human output
  with explicit JSON/JSONL. Multiple images require `--each` in the first release.
- Decision requests alone use non-streaming `POST /v1/systemone`, with top-level
  base64 images. Ordinary text/image requests retain their existing transports.
  Do not add temperatures, an SDK, silent fallback, or automatic server changes.
- Dispatch before ordinary file-only prompt/model assignment. Resolve CLI host
  overrides, environment, and category host in that order without global
  mutation. Preserve non-decision behavior, including `--ocr`.
- Acceptance requires parser/profile/routing/error/output tests, the full
  regression suite, packaged profile verification, and an isolated installed
  CLI smoke test. Report live testing separately from mocks. Update this spec,
  README, changelog, and continuity notes to match delivered behavior.

Implementation and release boundaries, exact schemas, input resolution, and
verification requirements are specified in PLAN-systemone.md. This planning
change does not implement the feature, alter runtime defaults, or authorize a
merge, tag, release, model download, or inference-server reconfiguration.

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

# Prompt from a file
ol -f prompt.txt
ol --file prompt.txt main.py

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

# Clipboard OCR
ol --ocr          # OCR the clipboard image with the configured vision model
ol --ocr -m llama3.2-vision
ol --ocr -h server -p 11434

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
  --ps, --loaded                  List models currently loaded in memory
  -m, --model MODEL               Model to use (default: from config)
  -d, --debug                     Show debug information including API request details
  -k, --keep                      Keep model loaded forever after this request
  -u, --unload                    Unload a model from memory
  --ocr                           OCR an image from the clipboard and replace the clipboard with the extracted text
  -h, --host HOST                 Ollama host (default: localhost). Overrides OLLAMA_HOST and configured hosts for this command.
  -p, --port PORT                 Ollama port (default: 11434). Overrides OLLAMA_HOST and configured hosts for this command.
  --set-default-model TYPE MODEL  Set default model for type (text or vision)
  --set-default-temperature TYPE TEMP  Set default temperature for type (text or vision)
  --set-default-host TYPE HOST    Set default host for type (text or vision). CLI flags -h/-p override configured hosts.
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

hosts:
  text: null              # Default host for text models (null = use OLLAMA_HOST or localhost)
  vision: null            # Default host for vision models (null = use OLLAMA_HOST or localhost)

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
  .pdf: 'Please summarize or extract the key points from this PDF document:'
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
