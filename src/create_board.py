"""
Admin CLI script to create a new board.

Usage: python -m src.create_board <board_name>

The board key is derived as the lowercase version of the name.
"""

import sys
from pathlib import Path

from src.database import Database
from src.services.board_service import BoardService


def main() -> None:
    """Create a board; key = lowercase name."""
    if len(sys.argv) != 2:  # noqa: PLR2004
        print(
            "Usage: python -m src.create_board <board_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    name = sys.argv[1].strip()
    key = name.lower()

    db = Database(db_path=Path("sqlite.db"))
    db.init()
    bs = BoardService(db)

    error = bs.create_board(name, key)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Board created: name='{name}' key='{key}'")


if __name__ == "__main__":
    main()
