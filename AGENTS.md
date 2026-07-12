# Agent System Status: [CUSTOMIZED]

Canonical instruction file for Grok Build, Codex, Claude Code, Cursor, and human contributors.

Read this file completely before changing code. When instructions conflict:

`project_spec.md` > `AGENTS.md` > `.crules/modes/*` > tool-specific entrypoints (`GROK.md`, native IDE rules)

## Project identity

This repository is **ol**: a Python CLI wrapper around the Ollama HTTP API for local
and remote Ollama instances (prompts, file injection, vision, Modelfiles, config).

- Package: `ol` (src layout under `src/ol/`)
- CLI entry point: `ol` → `ol.cli:main`
- Packaging: `pyproject.toml` (setuptools) + `src/ol/__init__.py` (`__version__`)
- Runtime config: `~/.config/ol/` (`config.yaml`, `history.yaml`, `templates/`, `cache/`)
- External dependency: Ollama (local or remote via `OLLAMA_HOST` / `-h`/`-p`)
- Authoritative product scope: `project_spec.md`

## Required reading before implementation

1. `AGENTS.md` (this file)
2. `project_spec.md`
3. Active task under `.crules/tasks/wip/` (if present)
4. Relevant swarm mode under `.crules/modes/` when acting as Manager or Coder
5. `README.md` / `CHANGELOG.md` when changing user-facing CLI behavior

## Swarm SOP (crules)

This repo uses the **Skeleton Swarm** workflow from crules.

| Path | Role |
|------|------|
| `.crules/modes/MANAGER.md` | Orchestrate, version, task pipeline — do not implement product code |
| `.crules/modes/CODER.md` | Implement atomic, tested changes from tasks / user request |
| `.crules/modes/GIT_POLICY.md` | Conventional commits, branching, secret scan, release |
| `.crules/modes/BOOTSTRAPPER.md` | Only when `AGENTS.md` status is `[TEMPLATE]` (not present here) |
| `.crules/tasks/{wip,review,done}/` | Markdown task files with acceptance criteria |
| `project_spec.md` | Single source of truth for scope and conventions |
| `.grok/rules/` | Always-on Grok project rules (SOP + style) |
| `.grok/agents/` | Optional Grok agent profiles (manager / coder / swarm) |

Default persona for implementation work: **Coder**.
Default persona for planning, commits, releases, backlog: **Manager**.

Shortcut keywords (act as Manager, then follow `GIT_POLICY.md`):

- **commit** — secret scan, version bump, verify CLI version, conventional commit
- **branch** — create `feat/` / `fix/` / `docs/` / `chore/` / `refactor/` branch
- **release** — verify version, changelog summary, tag, push tags

## Hard boundaries

1. Do not invent Ollama API fields or endpoints. Prefer real Ollama docs and
   behavior: text → `/api/generate`, images → `/api/chat` with base64 images.
2. Keep CLI surface stable: document any flag rename/removal as breaking.
3. Never use `pip install --break-system-packages`. Prefer `pipx`, project
   `.venv`, or `python3 -m ol`.
4. Never commit secrets, credentials, or private prompt/data dumps.
5. Do not expand scope into a full TUI chat client, multi-provider LLM hub, or
   GUI unless the user explicitly requests it and tasks cover it.
6. Respect `OLLAMA_HOST` / configured per-type hosts; CLI `-h`/`-p` override for
   the current command only.
7. Initialization (`initialize_ol`) runs on CLI execution, not on package import.

## Coding style (Python)

- Python 3.7+ (`requires-python = ">=3.7"`).
- Type hints on public functions; Google-style docstrings.
- Prefer existing deps (`PyYAML`, `requests`, `pypdf`, `argcomplete`, `packaging`,
  `gitpython`) over new production dependencies unless a task adds them.
- No `shell=True` in `subprocess` — pass argv lists.
- snake_case functions/vars; PascalCase only for classes.
- Match existing `src/ol/` module patterns (`cli.py`, `config.py`, `init.py`,
  `version.py`) before introducing new modules.
- Dev tooling: pytest, ruff, black, mypy (see `requirements-dev.txt`).

## Versioning and packaging

- Version strings must agree across:
  - `pyproject.toml` (`[project].version`) — **master**
  - `src/ol/__init__.py` (`__version__`)
  - Git tags when releasing (`vX.Y.Z`)
- Verify with: `python3 -m ol --version` (or package CLI equivalent).
- Bump rules: `feat` → minor, `fix`/`docs`/`chore`/`refactor` → patch,
  `BREAKING CHANGE` / `!` → major. Versions only increase (monotonic).
- On commit: base version = highest of pyproject, `__version__`, and tags.

## Testing discipline

- Prefer the smallest test that proves the change (pytest under `tests/`).
- Mock Ollama HTTP / subprocess; do not require a live Ollama for unit tests.
- Run relevant tests before claiming done, e.g.:
  - `python -m pytest tests/ -q`
  - or the project venv: `.venv/bin/python -m pytest tests/ -q`
- Do not weaken assertions to green a bad implementation.
- For CLI changes: cover argparse paths, host/env, file injection, and vision
  routing when those areas are touched.

## Git discipline

- Follow `.crules/modes/GIT_POLICY.md`.
- Conventional commits; imperative subject; max ~72 chars.
- Prefer feature branches; do not force-push `main`.
- Track `AGENTS.md`, `GROK.md`, `project_spec.md`, and `.grok/` in git.
- Existing multi-IDE rule trees (`.cursor/`, `.claude/`, etc.) are maintained by
  `crules`; prefer regenerating them over hand-editing when possible.

## Work discipline

- Minimum code that solves the stated problem. Nothing speculative.
- Touch only what you must. Clean up only your own mess.
- Surface tradeoffs; do not hide confusion.
- Define success criteria; loop until verified.
- When a task file exists, update acceptance criteria and Coder Notes before
  moving it `wip` → `review` → `done`.
- Cross-session continuity: `summary.txt`, `instructions.txt`, `ainotes.md`.

## Grok-specific layout

| Path | Purpose |
|------|---------|
| `GROK.md` | Thin Grok entrypoint → points here |
| `.grok/rules/*.md` | Auto-loaded project rules |
| `.grok/agents/*.md` | Named agent profiles (`manager`, `coder`, `swarm`) |

Use `grok inspect` to confirm rules and agents load.
