"""NiceGUI TODO Board — application entry point."""

import os
from pathlib import Path

from nicegui import ui

from src.db.database import Database
from src.services.board_service import BoardService
from src.services.export_service import ExportService
from src.ui.board_page import create_board_page

# ── Subpath support (e.g. https://entorb.net/nice-todo) ────────────
# Set NICEGUI_SUBPATH="/nice-todo" on the server (behind reverse proxy with
# --remove-prefix).  Leave unset locally for normal root-level access.
SUBPATH = os.environ.get("NICEGUI_SUBPATH", "")
_PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_FILE = _PROJECT_DIR / "sqlite.db"

db = Database(db_path=DB_FILE)
db.init()

board_service = BoardService(db)
export_service = ExportService()

create_board_page(board_service, export_service)

ui.run(title="TODO Board", port=8505, language="en-US", root_path=SUBPATH)
