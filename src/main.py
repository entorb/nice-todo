"""NiceGUI TODO Board — application entry point."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from nicegui import ui  # noqa: E402

from src.auth import setup_auth  # noqa: E402
from src.database import Database  # noqa: E402
from src.services.board_service import BoardService  # noqa: E402
from src.services.export_service import ExportService  # noqa: E402
from src.ui.board_page import create_board_page  # noqa: E402

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

setup_auth()
create_board_page(board_service, export_service)

ui.run(title="TODO Board", port=8505, language="en-US", root_path=SUBPATH)
