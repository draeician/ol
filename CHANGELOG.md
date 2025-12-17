# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.25] - 2025-12-17

### Added
- STDIN input support for piping and redirection
- Users can now pipe input: `echo "text" | ol` or `cat file.txt | ol`
- STDIN input is automatically used as prompt when no prompt argument provided
- STDIN input is combined with prompt argument when both provided

### Changed
- CLI now detects STDIN availability using `sys.stdin.isatty()`
- When STDIN is available (not a TTY), it's read and used as input
- Trailing newlines from STDIN are automatically removed

### Testing
- Added comprehensive test suite (7 tests) for STDIN input support:
  - STDIN used as prompt when no argument provided
  - STDIN combined with prompt argument
  - STDIN works with file arguments
  - No STDIN read when stdin is a TTY
  - Multiline input handling
  - Empty input handling
  - Trailing newline removal

## [0.1.24] - 2025-12-17

### Fixed
- Removed shell execution in update path (security fix)
- Update command now uses argument-list subprocess call instead of shell=True
- Prevents shell injection vulnerabilities

### Changed
- Update command parsing uses `shlex.split()` to safely convert command string to argument list
- Improved error handling for command parsing failures

### Testing
- Added comprehensive test suite (4 tests) for update command execution:
  - Verifies argument list usage (no shell execution)
  - Tests handling of URLs with special characters
  - Tests error surfacing for update failures
  - Tests handling of invalid command parsing

## [0.1.23] - 2025-12-17

### Changed
- Removed side effects on package import - importing `ol` no longer writes to `~/.config/ol`
- Initialization now happens only when CLI is invoked, not when package is imported

### Refactored
- Moved `initialize_ol()` call from `__init__.py` to `cli.py` main() function
- Package can now be imported without creating configuration directories

### Testing
- Added comprehensive test suite (6 tests) proving:
  - Importing package does not create config directory
  - Importing package does not call initialize_ol()
  - CLI invocation still initializes configuration correctly
  - All required directories and files are created on CLI execution

## [0.1.22] - 2025-12-17

### Fixed
- Implemented deep merge for configuration defaults so partial configs never drop nested keys
- Missing nested keys now remain populated from defaults when user config is partial
- Explicit user overrides win deterministically over defaults

### Changed
- Configuration loading now uses deep merge instead of shallow merge
- Partial user configs (e.g., only `models.text`) no longer lose other nested keys (e.g., `models.vision`)

### Testing
- Added comprehensive test suite for deep merge functionality (8 tests)
- Tests verify nested defaults are preserved and user overrides work correctly

## [0.1.21] - 2025-12-17

### Changed
- Vision and mixed-content requests now route through `/api/chat` endpoint instead of `/api/generate`
- Image requests use chat API payload format with `messages` array containing images
- Text-only requests continue using `/api/generate` endpoint with `prompt` field

### Fixed
- Improved support for multimodal content (text + images) by using structured chat API format
- Enforced strict payload contract: text-only requests have no `images` field, image requests always use `/api/chat`

### Testing
- Added tests to verify endpoint routing: text-only → `/api/generate`, image requests → `/api/chat`
- Added tests to verify payload structure for both endpoints
- Tests fail if routing logic breaks (guardrails)

## [0.1.20] - 2025-12-17

### Fixed
- Improved error handling to surface runtime errors consistently
- Replaced silent exception swallowing with explicit error handling throughout the codebase
- Debug mode (`-d`) now prints full exception details with traceback to stderr
- Normal mode now prints concise warnings to stderr instead of silently ignoring errors

### Changed
- Error handlers in config loading/saving, version management, hostname parsing, JSON parsing, and API streaming now surface errors appropriately
- Users will now see warnings when non-critical errors occur (e.g., config load failures, cache errors)

## [0.1.19] - 2025-12-17

### Changed
- Updated Python version requirement from 3.6+ to 3.7+ to match actual dependency requirements
- Updated test suite to validate HTTP API streaming execution path instead of subprocess calls

### Fixed
- Corrected README documentation: remote vision description now accurately reflects that images are base64-encoded in API payload
- Repository hygiene: added `.pytest_cache/` to `.gitignore` to prevent tracking of test artifacts

### Testing
- Refactored tests to mock `requests.post` instead of `subprocess.run` for API calls
- Added comprehensive test assertions for endpoint URL, temperature parameter, images field behavior, and streaming output
- Tests now provide authentic validation of the HTTP API execution path

## [0.1.18] - 2025-12-17

### Added
- Temperature control support for text and vision models
- `--set-default-temperature` CLI command to set default temperature per model type
- `--temperature` CLI option to override temperature for a single command
- Temperature defaults stored in configuration (default: 0.7 for both text and vision)
- `call_ollama_api()` function using Ollama HTTP API instead of subprocess for temperature support
- Temperature displayed in default configuration output

### Changed
- Switched from subprocess `ollama run` to HTTP API calls to support temperature parameter
- `run_ollama()` now accepts temperature parameter and uses API for all requests

## [0.1.17] - 2025-12-17

### Added
- `--set-default-model` CLI command to change default text or vision model
- `set_default_model()` function with validation for model types
- Users can now set default models without manually editing config.yaml

## [0.1.16] - 2025-12-17

### Added
- Display current configuration defaults when no arguments are provided
- `display_defaults()` function shows host, default text/vision models, and last used model

### Changed
- Replaced help message with defaults display when `ol` is run without arguments

## [0.1.15] - 2025-11-19

### Added
- Host/port selection via `-h/--host` and `-p/--port` overriding `OLLAMA_HOST` for the current command
- CLI flags allow setting Ollama host and port without using environment variables
- Support for local custom port usage: `ol -h localhost -p 11435 "Hello"`
- Support for remote host/port: `ol -h api.myhost.com -p 11434 -m codellama "Review this" file.py`
- Help flag changed to `--help` and `-?` (was `-h`)

### Changed
- Changed host flag from `-H` to `-h` to match common CLI conventions
- Changed help flag from `-h` to `--help` and `-?` to avoid conflict with host flag

### Fixed
- Fixed Modelfile filename to use hostname from `OLLAMA_HOST` (or `-h` flag) instead of local machine hostname when saving Modelfiles from remote instances

## [0.1.13] - 2024-12-20

### Added
- `--save-modelfile` flag to download and save a model's Modelfile to disk
- `-a, --all` flag to save Modelfiles for all installed models (requires --save-modelfile)
- `--output-dir` option to specify custom output directory for saved Modelfiles
- Support for remote Modelfile downloads via OLLAMA_HOST environment variable
- `list_installed_models()` helper function with JSON and text parsing fallback
- `sanitize_model_name()` function to safely handle model names with path-hostile characters
- Modelfile naming pattern: `<modelname>-<hostname>-<timestamp>.modelfile` (path-hostile characters replaced with underscores)

### Fixed
- Fixed `FileNotFoundError` when saving Modelfiles for models with slashes or other path-hostile characters in their names
- Improved error handling in `save_all_modelfiles()` to continue processing remaining models when one fails

## [0.1.12] - 2024-12-19

### Added
- Completed TODO item: models listing functionality fully integrated into ol command

### Changed
- Models listing now available via `-l` or `--list` flag in main ol command
- Update functionality integrated into main ol command with `--update` and `--check-updates` flags

### Removed
- Removed unused modeltest.py file
- Removed completed TODO item from TODO file

## [0.1.11] - 2024-03-12

### Changed
- Updated default vision model to llama3.2-vision
- Removed base64 encoding for images, using direct file paths for both local and remote instances
- Updated debug output to show correct commands for image processing

## [0.1.10] - 2024-03-12

### Fixed
- Fixed update command to use full git repository URL for pipx reinstall

## [0.1.9] - 2024-03-12

### Fixed
- Fixed update command to use full git repository URL for pipx reinstall

## [0.1.8] - 2024-03-12

### Fixed
- Fixed image processing to use base64 encoding for both local and remote instances

## [0.1.7] - 2024-03-19

### Added
- Support for detecting unsupported image formats
- Improved error handling for unsupported image formats with helpful conversion suggestions

### Changed
- Refactored image format handling to use maintainable sets of supported and unsupported formats

## [0.1.6] - 2024-03-19

### Fixed
- Fixed version update detection for pipx installations
- Improved version comparison handling
- Updated update command to use pipx reinstall

## [0.1.5] - 2024-03-19

### Fixed
- Fixed missing textwrap import in cli.py

## [0.1.4] - 2024-03-19

### Fixed
- Fixed debug output showing without -d flag
- Added proper debug flag handling in configuration

## [0.1.3] - 2024-03-19

### Fixed
- Fixed version flag not working due to prompt argument requirement
- Improved argument handling for version management commands

## [0.1.2] - 2024-03-19

### Added
- Added test for version flag functionality

### Fixed
- Fixed version flag not being recognized in CLI
- Fixed version information display in command line interface

## [0.1.1] - 2024-03-19

### Added
- Comprehensive test suite with 29 test cases
- Tests for error handling, configuration, image processing
- Tests for input processing, remote server handling
- Tests for command formatting and shell escaping

### Fixed
- Fixed model selection logic in tests
- Fixed subprocess mocking for image processing
- Fixed environment variable handling in tests

## [0.1.0] - 2023-12-02

### Added
- Initial release of the Ollama REPL wrapper
- Command-line interface for interacting with Ollama
- Support for both local and remote Ollama instances
- Configuration system with YAML-based settings
- Default prompts for different file types
- Vision model support for image analysis
- Debug mode for command inspection
- Automatic model selection based on file type
- Remote server support via OLLAMA_HOST environment variable
- Template system for common tasks
- Configuration directory at ~/.config/ol/
- Comprehensive documentation and examples 