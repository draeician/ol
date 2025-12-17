# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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