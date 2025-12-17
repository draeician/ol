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

