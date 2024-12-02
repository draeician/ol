# Ollama REPL Wrapper (ol)

A Python command-line utility that wraps the Ollama REPL, providing enhanced functionality and configuration options.

## Current Features

### Core Functionality
- Command-line interface to Ollama
- File content injection into prompts
- Model selection and management
- Debug output option
- Automatic configuration initialization during installation

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
  - Vision: llava
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
- Per-model configuration:
  - Temperature
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

# Debug mode
ol -d "Analyze this" data.json

# Using default prompts
ol main.py  # Uses Python code review template

# Multiple files
ol "Compare these" file1.py file2.py

# Image analysis
ol image.jpg  # Uses vision model automatically
```

## Command-Line Interface

```bash
ol [options] [prompt] [files...]

Options:
  -l, --list           List available models
  -m, --model MODEL    Model to use (default: from config)
  -d, --debug          Show debug information
  -h, --help          Show help message
```

## Configuration Structure

```yaml
models:
  text: llama3.2
  vision: llava
  last_used: null
  aliases:
    py: codellama
    js: codellama
    doc: llama3.2

default_prompts:
  .py: 'Review this Python code and provide suggestions for improvement:'
  .js: 'Review this JavaScript code and provide suggestions for improvement:'
  .md: 'Can you explain this markdown document?'
  # ... more file types

system_prompts:
  code_review: |
    You are a senior software engineer reviewing code.
    Focus on:
    - Code quality
    - Performance
    - Security
    - Best practices
  documentation: |
    You are a technical writer creating documentation.
    Focus on:
    - Clarity
    - Completeness
    - Examples
    - Use cases

templates:
  code_review: |
    Please review this {language} code:
    {content}
    Focus on:
    1. Code structure
    2. Error handling
    3. Performance
    4. Security

  compare: |
    Compare these files:
    File 1: {file1}
    File 2: {file2}
    
    Analyze:
    1. Similarities
    2. Differences
    3. Potential issues
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
