# Python coding style (ol)

Apply on any `*.py` edit under this repository.

## Language and packaging

- Target Python 3.7+ unless a task raises the floor.
- Package lives under `src/ol/` (src layout).
- Prefer existing production dependencies; do not add new ones without an explicit task.
- Entry point: `ol` → `ol.cli:main`.
- Config/data dir: `~/.config/ol/` (created by `initialize_ol` on CLI run, not import).

## Style

1. PEP 8 / Ruff-friendly layout; 4-space indent.
2. Type hints on public functions; return types included.
3. Google-style docstrings for public callables.
4. f-strings for formatting.
5. `snake_case` functions and variables; `PascalCase` classes only if introduced.
6. Prefer explicit `is None` checks for singletons.
7. Narrow `except` clauses; preserve causes when re-raising.
8. Use `with` for resources; no bare `open` without context managers.

## Subprocess, HTTP, and safety

- Always pass argv **lists** to `subprocess` — never `shell=True`.
- Prefer `requests` for Ollama HTTP streaming (existing `call_ollama_api` pattern).
- Do not use `pip install --break-system-packages`.
- Install with `pipx` or a project venv; ad-hoc via `python3 -m ol`.

## Domain-specific

- Text-only requests: `/api/generate`.
- Image / vision requests: `/api/chat` with base64 `images` on the user message.
- Host resolution order: CLI `-h`/`-p` → env `OLLAMA_HOST` → per-type config host → localhost.
- PDF text extraction via `pypdf`; warn and skip encrypted/empty PDFs.
- Image formats: support common raster types; fail clearly on unsupported (e.g. webp/svg).
- Keep argcomplete completers wired for path/model/type arguments when adding CLI flags.

## Structure preference

Keep changes local to existing modules until size or clarity demands a split:

| Module | Responsibility |
|--------|----------------|
| `cli.py` | argparse, orchestration, Ollama calls |
| `config.py` | YAML config load/save, defaults |
| `init.py` | first-run dirs and templates |
| `version.py` | update check / version manager |

If splitting, preserve the public CLI flag surface.

## Tests

- Prefer pure-function unit tests for helpers (sanitize, host parse, prompts).
- Mock network and `subprocess`; unit suite should not need a live Ollama.
- Do not weaken tests to pass a bad change.
- Name tests clearly; one concern per test function.
