# NiceTODO — Kanban board

Single-package app: NiceGUI + SQLModel + SQLite.

## Dev commands

| Action | Command |
| ------ | ------- |
| Run | `uv run python -m src.main` (port 8505) |
| Ruff check | `uv run ruff check .` |
| Ruff format | `uv run ruff format .` |
| Test | `uv run pytest` |
| Pre-commit | `uv run pre-commit run --all-files` |
| CI-local equivalent | `uv run --frozen ruff format --check && uv run --frozen ruff check --no-fix --output-format=github && uv run --frozen pytest --cov && uv run --frozen pre-commit run --all-files` |

Admin scripts: `scripts/create_board.sh <name>`, `scripts/delete_board.sh <id_or_key>`.

## Ruff

Config in `ruff.toml`. All rules enabled, line-length 88.
Commands run on **whole repo**, never single files.

Notable ignores: `S101` asserted in tests only, `T201` (print), `ERA` (commented code), `COM812`, `ISC001`, `RET504`, `FIX002`, `PGH003`, `TD002`, `TD003`, some docstring rules.

Quirks:

- `ruff: noqa: E402` before `nicegui` import in `main.py` — `load_dotenv()` must run first
- `ruff: noqa: D107` on `__init__` methods where appropriate
- `ruff: noqa: FBT001` on bool-flag params (project convention)

## Architecture

```text
src/main.py               -> entrypoint
src/auth.py               -> cookie-based single-user API-key auth
src/database.py           -> SQLModel wrapper, auto-creates tables + runs ALTER TABLE migrations on startup
src/models.py             -> Board -> Column -> Card, Label (global)
src/services/             -> board_service (orchestration), export_service, sort
src/ui/                   -> board_page, column_component, card_component, dialogs, _shared
```

Models: `Board` has `Column` children, `Column` has `Card` children — cascade delete via `Relationship()`.
`Column.__tablename__ = "column_"` (SQL reserved-word).
`Card.is_completed` is a computed property (`date_completed is not None`).

## Env

Required: `NICEGUI_API_KEY`. Optional: `NICEGUI_SUBPATH` (e.g. `/nice-todo` for reverse proxy).
All URLs injected into HTML must use `SUBPATH` prefix.
Secrets in `.env` (gitignored). `.env_EXAMPLE` shows format.

## Style

- Python 3.11
- Strict type hints
- 1-liner docstrings
- Write ruff-compatible code from start — don't write things autofix will break
- Update this file when new high-signal info emerges

## Caveman speech

Respond like smart caveman. Cut all filler, keep technical substance.

- Drop articles (a, an, the), filler (just, really, basically, actually).
- Drop pleasantries (sure, certainly, happy to).
- No hedging. Fragments fine. Short synonyms.
- Technical terms stay exact. Code blocks unchanged.
- Pattern: [thing] [action] [reason]. [next step].
