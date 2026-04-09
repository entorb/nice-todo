"""NiceGUI TODO Board — application entry point."""

import os
from pathlib import Path

from dotenv import load_dotenv

# ruff: noqa: E402
load_dotenv()

from nicegui import app, ui

from src.auth import setup_auth
from src.database import Database
from src.services.board_service import BoardService
from src.services.export_service import ExportService
from src.ui.board_page import create_board_page

# Subpath support (e.g. https://entorb.net/nice-todo)
# Set NICEGUI_SUBPATH="/nice-todo" on the server (behind reverse proxy with
# --remove-prefix).  Leave unset locally for normal root-level access.
SUBPATH = os.environ.get("NICEGUI_SUBPATH", "")
_PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_FILE = _PROJECT_DIR / "sqlite.db"

ICON = _PROJECT_DIR / "src/icons/favicon.svg"
assert ICON.is_file(), f"Icon not found: {ICON}"

APPLE_ICON = _PROJECT_DIR / "src/icons/apple-touch-icon.png"
assert APPLE_ICON.is_file(), f"Apple touch icon not found: {APPLE_ICON}"
APPLE_ICON_URL = f"{SUBPATH}/apple-touch-icon.png"
app.add_static_file(local_file=APPLE_ICON, url_path="/apple-touch-icon.png")

db = Database(db_path=DB_FILE)
db.init()

board_service = BoardService(db)
export_service = ExportService()

setup_auth()
create_board_page(
    board_service=board_service,
    export_service=export_service,
    apple_icon_url=APPLE_ICON_URL,
)

ui.run(
    title="TODO Board",
    port=8505,
    language="en-US",
    root_path=SUBPATH,
    favicon=ICON,
)
