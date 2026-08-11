# NiceTODO — Kanban board

Single-package app: NiceGUI + SQLModel + SQLite.

## Dev commands

| Action | Command |
| ------ | ------- |
| Run | `uv run python -m src.main` (port 8505) |
| Ruff format and lint | `uv run ruff format && uv run ruff check --fix` |
| All checks | `scripts/run_checks.sh` (runs all `scripts/chk_*.sh`) |

Admin scripts: `scripts/create_board.sh <name>`, `scripts/delete_board.sh <id_or_key>`.

## Local testing

1. `cp .env_EXAMPLE .env`, set `NICEGUI_API_KEY` (any string locally)
2. `uv run python -m src.main` → <http://localhost:8505> (port 8505)
3. Login with the key; no boards yet → create one: `scripts/create_board.sh <name>` then reload
4. SQLite DB at `sqlite.db` (gitignored); delete test boards via `scripts/delete_board.sh <id_or_key>`

Note: `NICEGUI_SUBPATH` stays empty locally — set only behind reverse proxy.
`last_login` bumps on first login/board create/board switch, not on card edits or reloads.

### CLI smoke-test the UI (curl)

Server must be running (step 2 above). No browser needed:

```sh
# login -> store auth cookie in /tmp/cj.txt
curl -s -c /tmp/cj.txt -o /dev/null -X POST \
  -d "key=<your key>" http://127.0.0.1:8505/login/submit

# fetch board page (board must exist: scripts/create_board.sh <name>)
curl -s -b /tmp/cj.txt "http://127.0.0.1:8505/?key=<board_key>" -o /tmp/page.html

# unauthenticated requests -> 403 (or 303 redirect to /login)
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8505/?key=<board_key>"
```

Cookie jar `/tmp/cj.txt` required — the auth middleware blocks requests without the cookie.
`/login`, `/logout`, and `/_nicegui/` are public; everything else needs the cookie.

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
src/database.py           -> SQLModel wrapper, auto-creates tables + explicit migrations via Database._migrate() on startup
src/models.py             -> Board -> Column -> Card, Label (global)
src/services/             -> export_service, sort
src/ui/                   -> board_page, column_component, card_component, dialogs, _shared
```

Models: `Board` has `Column` children, `Column` has `Card` children — cascade delete via `Relationship()`.
`Column.__tablename__ = "column_"` (SQL reserved-word).
`Card.is_completed` is a computed property (`date_completed is not None`).

## Datetime convention

All datetimes are stored as **naive UTC** (`datetime.now(tz=UTC).replace(tzinfo=None)`,
helper `src.models.utcnow`). Never store local time or tz-aware datetimes — SQLite has no
timezone type. Use `models.utcnow` for defaults and comparisons; the existing `date_created`
and `date_completed` values in dev DBs were created under the same convention.

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
