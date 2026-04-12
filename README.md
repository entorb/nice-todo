# Nice TODO

A Kanban-style task board built with NiceGUI and SQLModel.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```sh
uv sync
```

Create a `.env` file in the project root with your secret access key:

```sh
NICEGUI_API_KEY="your-random-secret"
```

Generate a key with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

## Run

```sh
uv run python -m src.main
```

Open <http://localhost:8505/> in your browser. On first visit per device you'll be asked for the access key once; a persistent cookie is set so you won't be asked again.

## Admin: Delete a Board

```sh
uv run python -m src.delete_board <board_id_or_key>
python3.11 -m src.delete_board <board_id_or_key>
```

## Tech Stack

- **NiceGUI** — Python web UI framework
- **SQLModel** — ORM (SQLAlchemy + Pydantic)
- **SQLite** — persistence (`sqlite.db`, auto-created on first run)

## SonarQube Code Analysis

- Report at [sonarcloud.io](https://sonarcloud.io/summary/overall?id=entorb_nice-todo&branch=main)
- Or per API as [json](https://sonarcloud.io/api/issues/search?componentKeys=entorb_nice-todo&ps=500)

## Uberspace Hosting

`~/etc/services.d/nice-todo.ini`

```ini
[program:nice-todo]
directory=%(ENV_HOME)s/nice-todo
command=python3.11 -O -m src.main
# `startsecs` is set by Uberspace monitoring team, to prevent a broken service from looping
startsecs=30
```

Configuration is read from `.env` in the project root (see Setup above). On the server, `NICEGUI_SUBPATH="/nice-todo"` must be set, locally that is not needed:

```sh
NICEGUI_API_KEY="your-random-secret"
NICEGUI_SUBPATH="/nice-todo"
```

install backend service

```sh
uberspace web backend set /nice-todo --http --port 8505 --remove-prefix
```

logs

```sh
supervisorctl tail -f nice-todo
```
