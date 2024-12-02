# ol - Ollama REPL Wrapper

A Python command-line wrapper for the Ollama REPL.

## Prerequisites

- Python 3.6 or higher
- Ollama installed and available in your system PATH
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

### Default Templates

The tool comes with several pre-configured templates in `~/.config/ol/templates/`:

1. `code_review.yaml` - Comprehensive code review template
   - Code quality analysis
   - Performance review
   - Security assessment
   - Best practices evaluation

2. `documentation.yaml` - Documentation generation template
   - Overview generation
   - Technical details
   - Usage examples

3. `bug_analysis.yaml` - Bug analysis and fixing template
   - Bug description
   - Root cause analysis
   - Solution proposals

4. `compare_files.yaml` - File comparison template
   - Content analysis
   - Quality assessment
   - Improvement recommendations

Each template is customizable and includes:
- Template name and description
- Structured prompt format
- Variable definitions
- Required and optional parameters

Example template structure:

```yaml
name: Code Review
description: Template for code review with customizable focus areas
template: |
    Please review this {language} code with a focus on:
    [template content]
variables:
    language:
        description: Programming language of the code
        default: Python
    content:
        description: The code content to review
        required: true
```

The configuration system provides:
- Different default models for text and vision tasks
- Remembers the last used model
- Default prompts for different file types
- Automatic model selection based on file type (vision model for images)

## Usage

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

- `-l, --list`: List available models
- `-m MODEL, --model MODEL`: Specify the model to use (default: from config)
- `-d, --debug`: Show debug information (input processing and prompt construction)
- `"PROMPT"`: The prompt to send to Ollama (optional if files are provided)
- `FILES`: Optional files to inject into the prompt

## Debug Output

When using the `-d` or `--debug` flag, you'll see detailed information about:
- The model being used
- The base prompt
- Files being processed
- Content length of each file
- The final constructed prompt
- The Ollama command being executed

Example debug output:
```
=== Debug Information ===
Model: llama3.2
Base Prompt: Can you tell me about this file?
Files to process: ['./project_spec.md']

Added content from ./project_spec.md
File content length: 1234 characters

=== Final Prompt ===
Can you tell me about this file?

Content of ./project_spec.md:
[file contents here]

=== Sending to Ollama ===
Command: ollama run llama3.2
```

## Examples

```bash
# Get code review with debug information
ol -d "Review this code and suggest improvements" main.py

# Generate documentation (using default prompt)
ol source.py

# Ask questions about multiple files
ol "How do these files interact?" file1.py file2.py

# Analyze an image (automatically uses vision model)
ol image.jpg
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