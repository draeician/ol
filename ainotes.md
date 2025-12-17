# AI Notes

## Branch 1: Packaging and Docs Metadata (chore/packaging-docs-metadata)

### Changes Made

#### Python Version Requirement Correction
- Updated `pyproject.toml`:
  - Changed `requires-python` from `">=3.6"` to `">=3.7"`
  - Removed `"Programming Language :: Python :: 3.6"` classifier
  - Rationale: Dependencies require Python 3.7+:
    - `packaging>=23.0` requires Python 3.7+
    - `gitpython>=3.1.0` requires Python 3.7+

#### README Documentation Corrections
- **Prerequisites section**: Updated "Python 3.6 or higher" to "Python 3.7 or higher"
- **Remote Vision Models section**: Corrected description to accurately reflect implementation:
  - Previous (incorrect): "The image path will be included in the prompt"
  - Updated: Images are base64-encoded and sent in the API payload via the `images` field, not as file paths in the prompt text

### Notes for CHANGELOG
These corrections align the packaging metadata and documentation with the actual dependency requirements and implementation behavior. No functional code changes were made.

## Branch 2: Repo Hygiene (chore/repo-hygiene)

### Changes Made
- Updated `.gitignore`: Added `.pytest_cache/` to ensure pytest cache directories are ignored
- Verified that all build artifacts (`src/ol.egg-info/`, `build/`, `__pycache__/`, `.pytest_cache/`) are properly ignored and not tracked in git
- Confirmed packaging and imports still work correctly after hygiene cleanup

### Notes for CHANGELOG
Repository hygiene improvements ensure generated build/test artifacts are properly ignored and won't cause churn in future commits.

## Branch 3: HTTP API Test Suite (test/http-api-suite)

### Changes Made

#### Test Refactoring
- Refactored tests to mock `requests.post` instead of `subprocess.run` for HTTP API calls
- Created helper function `create_mock_streaming_response()` to simulate line-delimited JSON streaming responses
- Updated all tests that previously tested `ollama run` subprocess calls to test HTTP API behavior instead

#### Test Assertions Added
- **Endpoint URL validation**: Tests verify that `OLLAMA_HOST` is correctly used in API endpoint URLs
- **Temperature validation**: Tests verify that temperature parameter is included in payload with expected values
- **Images field validation**: Tests verify that:
  - Images are base64-encoded and included in payload for vision requests
  - Images field is NOT included in text-only requests
  - Multiple images are handled correctly
- **Streaming output validation**: Tests verify that streaming responses are correctly parsed and emitted

#### Subprocess Tests Retained
- Kept subprocess tests for `ollama list` (model listing)
- Kept subprocess tests for `ollama show --modelfile` (Modelfile saving)
- These operations still use subprocess and are not part of the HTTP API path

#### Design Decisions
- Tests now validate the actual HTTP API execution path, providing authentic testing
- Mock responses use realistic line-delimited JSON format matching Ollama's actual API responses
- Tests fail when underlying logic breaks, serving as guardrails for the HTTP API implementation

### Notes for CHANGELOG
Test suite now validates HTTP API streaming execution path instead of subprocess calls, ensuring tests accurately reflect the actual implementation behavior. This provides authentic testing that will catch regressions in the API integration.

## Branch 4: Error Surfacing (fix/error-surfacing)

### Changes Made

#### Error Handling Improvements
- Replaced silent exception swallowing with explicit error handling throughout the codebase
- **Debug mode**: Prints full exception details with traceback to stderr
- **Normal mode**: Prints concise warnings to stderr

#### Specific Fixes
- **`get_hostname_for_filename()`**: Now surfaces URL parsing errors instead of silently falling back
- **`list_installed_models()`**: Now warns when JSON parsing fails, not just in debug mode
- **`call_ollama_api()`**: Now warns about JSON decode errors in streaming responses
- **`Config._load_config()`**: Now surfaces config loading errors with appropriate detail level
- **`Config._save_config()`**: Now surfaces config saving errors with appropriate detail level
- **`VersionManager`**: All error handlers now surface errors appropriately:
  - `_load_version_info()`: Warns on load failures
  - `_load_cache()`: Warns on cache read failures
  - `_save_cache()`: Warns on cache write failures
  - `_save_version_info()`: Warns on save failures
  - `fetch_latest_version()`: Warns on network/parsing failures
  - `check_local_repository()`: Warns on git check failures (debug mode only)

#### Test Coverage
- Added tests to verify errors are surfaced properly:
  - Config load failure tests
  - JSON parsing error tests
  - Hostname parsing error tests
  - Version cache error tests
- Tests verify that warnings appear in normal mode and full details appear in debug mode

### Design Decisions
- Errors are now consistently surfaced rather than silently ignored
- Debug mode provides full context for troubleshooting
- Normal mode provides user-friendly warnings without overwhelming output
- Critical errors (like file I/O failures in main execution path) still exit with error codes
- Non-critical errors (like cache/version check failures) warn but allow execution to continue

### Notes for CHANGELOG
This change improves observability by ensuring all runtime errors are visible to users. Debug mode provides full diagnostic information, while normal mode provides concise warnings that don't overwhelm the output.

## Branch 5: Vision/Mixed Contract (fix/vision-mixed-contract)

### Changes Made

#### Endpoint Routing
- **Image requests**: Now route to `/api/chat` endpoint
- **Text-only requests**: Continue using `/api/generate` endpoint
- **No silent fallbacks**: If `/api/chat` fails, an explicit error is raised (no automatic fallback to `/api/generate`)

#### Payload Contract

**Text-only requests (`/api/generate`):**
- Endpoint: `{base_url}/api/generate`
- Payload format:
  ```json
  {
    "model": "model_name",
    "prompt": "text prompt",
    "temperature": 0.7,
    "stream": true
  }
  ```
- **Contract**: No `images` field in payload
- **Contract**: No `messages` field in payload

**Image requests (`/api/chat`):**
- Endpoint: `{base_url}/api/chat`
- Payload format:
  ```json
  {
    "model": "model_name",
    "messages": [
      {
        "role": "user",
        "content": "text prompt",
        "images": ["base64_image1", "base64_image2"]
      }
    ],
    "temperature": 0.7,
    "stream": true
  }
  ```
- **Contract**: Always use `/api/chat` when any images are present
- **Contract**: Images are included in the `messages[0].images` array
- **Contract**: No `prompt` field in payload (uses `messages[].content` instead)

#### Test Updates
- Added tests to verify endpoint routing:
  - Text-only requests → `/api/generate`
  - Image requests → `/api/chat`
- Added tests to verify payload structure:
  - Text-only: `prompt` field, no `images`, no `messages`
  - Image requests: `messages` array with `images`, no `prompt` field
- Tests fail if routing logic breaks (guardrails)

#### Design Decisions
- **Why `/api/chat` for images?**: The chat API provides better support for multimodal content (text + images) in a structured format
- **No fallback strategy**: Explicit errors are preferred over silent fallbacks. If `/api/chat` causes issues, the entire PR can be reverted cleanly rather than adding hidden fallback logic
- **Isolated change**: This change is isolated to the `call_ollama_api()` function, making it easy to revert if needed
- **Backward compatibility**: Text-only requests continue to work exactly as before

### Notes for CHANGELOG
Vision and mixed-content requests now route through `/api/chat` endpoint with a strict payload contract. Text-only requests continue using `/api/generate`. This change improves support for multimodal content while maintaining backward compatibility for text-only usage.

