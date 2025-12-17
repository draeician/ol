## Feature-branch plan (priority order)

### Merge order

1. **Docs + packaging metadata** (low hanging fruit)
2. **Repo hygiene** (removes noise before big diffs)
3. **Testing aligned to HTTP API** (gets guardrails online)
4. **Fixes/hardening branches** (error surfacing, vision/mixed-content contract, config merge, init side-effects, update command security)
5. **Release branch** (version + changelog + final verification)

I’m keeping **version bump + CHANGELOG** edits isolated to the **release branch** to avoid merge conflicts across many pull requests (PRs).

---

## Branch 1 — `chore/packaging-docs-metadata` ✅ COMPLETED

**Goal:** correct requirements + docs that are already wrong today.

**Tasks**

* Update `pyproject.toml` Python requirement to match dependency reality.
* Update classifiers accordingly.
* Update README prerequisites (Python version) and correct remote vision description to match current behavior.
* Record what changed in `ainotes.md` for later CHANGELOG entry.

**Cursor prompt**

* Use GitHub MCP. From `main`, create branch `chore/packaging-docs-metadata`.
* Edit files using **`cat << 'EOF' > file`** workflow and audit with `vi`.
* Update:

  * `pyproject.toml` (`requires-python`, classifiers)
  * `README.md` prerequisites + usage notes that are incorrect
* Append this prompt to `instructions.txt` (separator `---`) and update `summary.txt`.
* Run tests with pipx venv command from repo rules.
* Commit with: `chore: align python requirements and docs`
* Open a PR to `main`, ensure checks pass, merge.

---

## Branch 2 — `chore/repo-hygiene` ✅ COMPLETED

**Goal:** remove generated artifacts from git to reduce churn.

**Tasks**

* Remove committed build/test artifacts (`src/ol.egg-info/`, `.pytest_cache/`).
* Add ignore rules in `.gitignore`.
* Verify packaging/tests still operate.

**Cursor prompt**

* From updated `main`, create branch `chore/repo-hygiene`.
* Remove tracked artifacts and update `.gitignore`.
* Update `instructions.txt` and `summary.txt`.
* Run full tests via pipx venv command.
* Commit: `chore: remove generated artifacts from repo`
* PR → checks → merge.

---

## Branch 3 — `test/http-api-suite` ✅ COMPLETED

**Goal:** get authentic testing online for the current HTTP API execution path.

**Tasks**

* Refactor tests that currently assert `subprocess.run(['ollama','run',...])` so they validate **`requests.post()` streaming** behavior.
* Ensure tests validate the **payload contract** (model, prompt, temperature, images presence rules).
* Ensure tests fail when underlying logic breaks (guardrail: “authentic testing”).

**Cursor prompt**

* From updated `main`, create branch `test/http-api-suite`.
* Update tests to mock `requests.post` and its streaming `iter_lines()` with realistic line-delimited JSON.
* Add assertions that verify:

  * endpoint URL uses `OLLAMA_HOST` when set
  * payload contains `temperature` with expected value
  * `images` field behavior matches current contract
  * streamed output is emitted correctly
* Keep subprocess tests for `ollama list` and `ollama show --modelfile`.
* Update `instructions.txt`, `summary.txt`, and note design decisions in `ainotes.md`.
* Run full tests; commit: `test: validate HTTP API streaming execution`
* PR → checks → merge.

---

## Fix branches (after tests are enforcing reality)

### Branch 4 — `fix/error-surfacing` ✅ COMPLETED

**Goal:** remove silent ignore paths; raise explicit failures or emit clear warnings (debug shows full context).

**Cursor prompt**

* Create branch `fix/error-surfacing`.
* Replace silent exception swallowing with explicit handling:

  * debug mode prints full exception details to stderr
  * normal mode prints concise warning to stderr
* Add/adjust tests that fail if errors are hidden.
* Update `instructions.txt` / `summary.txt` / `ainotes.md`.
* Run full tests; commit: `fix: surface runtime errors consistently`
* PR → checks → merge.

---

### Branch 5 — `fix/vision-mixed-contract` ✅ COMPLETED (updated: try **chat**, revert if issues)

**Goal:** route vision + mixed-content through **`/api/chat`** with a strict payload contract; keep the change isolated so we can revert cleanly if it misbehaves in real environments.

**Rules for this branch**

* **Primary path:** use `/api/chat` for any request that includes image(s).
* **No silent fallbacks:** do **not** try `/api/generate` automatically if chat fails. If chat fails, raise an explicit error.
* **Revert strategy:** if this causes problems after merge, we revert the entire PR (or reintroduce `/api/generate` in a new PR) rather than adding hidden fallback logic.

**Tasks**

* Implement `/api/chat` call path for image inputs (vision and mixed).
* Ensure text-only requests stay on the existing `/api/generate` path.
* Enforce contract:

  * text-only: **no `images`**
  * any images present: **always use `/api/chat`**, include images in the expected chat payload format
* Update tests to lock in endpoint selection + payload structure + streaming behavior for chat.
* Update `ainotes.md` with the payload contract and reasoning (“chat for images; no fallback; revert via PR if needed”).

**Cursor prompt**

* From latest `main`, create branch `fix/vision-mixed-contract`.
* Implement `/api/chat` for any invocation with `image_files`:

  * Build a chat payload with messages that include the prompt + images (use the Ollama-supported image field format for chat).
  * Stream responses and print output equivalently to the generate path.
* Keep `/api/generate` for text-only requests as-is.
* Add tests that must fail if:

  * images route to `/api/generate`
  * text-only routes to `/api/chat`
  * payload omits images when present
  * payload includes images when none provided
  * streaming parsing breaks (stops early / prints nothing)
* Update `instructions.txt` (append this prompt with `---`) and update `summary.txt`.
* Run the full test suite via the pipx venv command from `.cursorrules`.
* Commit: `fix: route image requests through /api/chat`
* Open PR to `main`, ensure checks pass, merge.

**Post-merge validation checklist**

* Manual smoke tests (local and remote):

  * text prompt only
  * image prompt only
  * mixed text + image
* If any serious incompatibility shows up: **revert this PR** (clean rollback), then open a follow-up branch to adjust approach explicitly.

---

### Branch 6 — `fix/config-deep-merge` ✅ COMPLETED

**Goal:** deep-merge defaults so partial configs never drop nested keys.

**Cursor prompt**

* Create branch `fix/config-deep-merge`.
* Implement deep merge for nested sections and add tests proving:

  * missing nested keys remain populated from defaults
  * explicit user overrides win deterministically
* Update `instructions.txt` / `summary.txt`.
* Run tests; commit: `fix: deep-merge configuration defaults`
* **IMPORTANT REMINDERS:**
  * Open PR to `main`, ensure checks pass, **merge the PR**
  * After merge, **switch back to main** and pull latest changes
  * **Delete the local feature branch** after merge
  * **Update version numbers** if this is a release (see release branch instructions)

---

### Branch 7 — `refactor/init-from-cli` ✅ COMPLETED

**Goal:** remove side effects on import; initialize on CLI execution path.

**Cursor prompt**

* Create branch `refactor/init-from-cli`.
* Move initialization so importing the package does not write to `~/.config/ol`.
* Add tests proving import is clean, while CLI invocation still initializes.
* Update `instructions.txt` / `summary.txt`.
* Run tests; commit: `refactor: move initialization to CLI execution`
* **IMPORTANT REMINDERS:**
  * Open PR to `main`, ensure checks pass, **merge the PR**
  * After merge, **switch back to main** and pull latest changes
  * **Delete the local feature branch** after merge
  * **Update version numbers** if this is a release (see release branch instructions)

---

### Branch 8 — `fix/update-no-shell` ✅ COMPLETED

**Goal:** remove shell execution in update path (security).

**Cursor prompt**

* Create branch `fix/update-no-shell`.
* Replace shell-based update execution with a direct argument-list subprocess call.
* Add tests validating invocation and failure surfacing.
* Update `instructions.txt` / `summary.txt`.
* Run tests; commit: `fix: execute update command without shell`
* **IMPORTANT REMINDERS:**
  * Open PR to `main`, ensure checks pass, **merge the PR**
  * After merge, **switch back to main** and pull latest changes
  * **Delete the local feature branch** after merge
  * **Update version numbers** if this is a release (see release branch instructions)

---

### Branch 9 — `feat/stdin-input-support` ✅ COMPLETED

**Goal:** add STDIN input support for piping and redirection.

**Cursor prompt**

* Create branch `feat/stdin-input-support`.
* Add STDIN input support so users can pipe input:
  * `echo "text" | ol`
  * `cat file.txt | ol`
  * `ol < file.txt`
* When STDIN is available (not a TTY), read from stdin and use as prompt or file content
* Handle both text and binary input appropriately
* If both STDIN and prompt argument are provided, STDIN should take precedence or be combined
* Add tests proving STDIN input works correctly
* Update `instructions.txt` / `summary.txt`.
* **IMPORTANT REMINDERS:**
  * **Bump version to 0.1.25 BEFORE committing**
  * Run tests; commit: `feat: add STDIN input support`
  * Open PR to `main`, ensure checks pass, **merge the PR**
  * After merge, **switch back to main** and pull latest changes
  * **Delete the local feature branch** after merge

---

## Final branch — `release/0.1.25` ✅ COMPLETED

**Goal:** versioning, changelog, final verification, tag.

**Cursor prompt**

* From latest `main`, create branch `release/0.1.24` (or appropriate next version).
* **Bump version in ALL required files:**
  * `src/ol/__init__.py` - Update `__version__`
  * `pyproject.toml` - Update `version` field
* Update `CHANGELOG.md` with a complete version section capturing all merged PRs since last release.
* Update `summary.txt` and append prompt to `instructions.txt`.
* Run full tests (pipx venv command), verify green.
* **IMPORTANT REMINDERS:**
  * **Commit all changes** with appropriate commit message
  * Open PR to `main`, ensure checks pass, **merge the PR**
  * After merge, **switch back to main** and pull latest changes
  * **Delete the local release branch** after merge
  * **Tag the release**: `git tag v0.1.24` (or appropriate version)
  * **Push tags**: `git push origin v0.1.24` (or use GitHub MCP to push tags)
  * Verify version is correct: `pipx reinstall ol` should show new version

---

Reply with **`chat`** or **`generate`** for the vision endpoint choice, and I'll lock Branch 5's prompt to that path.

