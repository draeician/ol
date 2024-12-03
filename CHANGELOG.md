# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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