# Python

- use Python 3.11 and best practice
- use uv to install packages and to run the application
- use strict type hints
- use 1-liner doc strings
- use best practice as of 2026
- run `uv run ruff check` and `uv run ruff format` after each new feature is implemented, and fix all findings
- write ruff-compatible code from the start: do not write code that ruff autofix will break (e.g. avoid top-level imports only used inside nested functions; verify the file is correct before running ruff)
- pytest unit tests are not a requirement (yet) add only the most important ones
- secrets and config are stored in `.env` (never commit this file); the app requires `NICEGUI_API_KEY` to be set
- Update AGENTS.md when needed to make the AI coding more efficient
- the app supports running behind a reverse proxy at a subpath via `NICEGUI_SUBPATH` env var (e.g. `/nice-todo`); all URLs for static assets, icons, and links injected into HTML must be prefixed with `SUBPATH` so they resolve correctly in production
