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

