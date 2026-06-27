"""
Admin CLI script to create a new board.

Usage: python -m src.create_board <board_name>

The board key is derived as the lowercase version of the name.
"""

import sys
from pathlib import Path

from src.database import Database


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

    result = db.add_board(key, name)
    if isinstance(result, str):
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"Board created: name='{name}' key='{key}'")


if __name__ == "__main__":
    main()
