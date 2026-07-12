# Swarm SOP (always on)

You operate in a multi-agent (Skeleton Swarm) repository. Native Grok rules
are loaded; also obey root `AGENTS.md`.

## Priority

`project_spec.md` > `AGENTS.md` > `.crules/modes/*` > this file

## Personas

| Mode | When | File |
|------|------|------|
| Manager | planning, backlog, commit/branch/release | `.crules/modes/MANAGER.md` |
| Coder | implementation and tests | `.crules/modes/CODER.md` |
| Git policy | any VCS mutation | `.crules/modes/GIT_POLICY.md` |

Default for coding requests: **Coder**. Default for “commit” / “release” / roadmap: **Manager**.

## Session checklist

1. Read `AGENTS.md` and `project_spec.md` when starting non-trivial work.
2. Track non-trivial work as Markdown under `.crules/tasks/wip/` with acceptance criteria.
3. Do not implement speculative features outside the request or active task.
4. Never use `--break-system-packages`. Prefer `pipx`, venv, or `python3 -m ol`.
5. Prefer regenerating multi-IDE rules via `crules` over hand-editing them.

## Important files

| File | Use |
|------|-----|
| `project_spec.md` | Scope, CLI surface, features |
| `AGENTS.md` | Hard boundaries and coding rules |
| `GROK.md` | Grok entrypoint |
| `CHANGELOG.md` | Version history |
| `summary.txt` / `instructions.txt` / `ainotes.md` | Cross-session continuity |
| `.grok/agents/` | Optional named agent profiles |

## Verification

Before claiming done:

- Smoke: `python3 -m ol --help` and/or `python3 -m ol --version`
- If version touched: CLI version matches `pyproject.toml` and `src/ol/__init__.py`
- If logic touched: relevant `pytest` under `tests/`
