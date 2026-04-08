"""
Admin CLI script to delete a board and all associated data.

Usage: python -m src.delete_board <board_id_or_key>
"""

import sys
from pathlib import Path

from sqlmodel import select

from src.database import Database
from src.models import Board

_EXPECTED_ARGS = 2


def main() -> None:
    """Delete a board by ID or key."""
    if len(sys.argv) != _EXPECTED_ARGS:
        print(
            "Usage: python -m src.delete_board <board_id_or_key>",
            file=sys.stderr,
        )
        sys.exit(1)

    identifier = sys.argv[1]
    db = Database(db_path=Path("sqlite.db"))

    # Try as key first, then as integer ID
    board = db.get_board_by_key(identifier)
    if board is None:
        try:
            board_id = int(identifier)
        except ValueError:
            print(f"Error: Board '{identifier}' not found.", file=sys.stderr)
            sys.exit(1)
        with db.session() as s:
            board = s.exec(select(Board).where(Board.id == board_id)).first()

    if board is None:
        print(f"Error: Board '{identifier}' not found.", file=sys.stderr)
        sys.exit(1)

    db.delete_board(board.id)  # type: ignore[arg-type]
    print(f"Board {board.id} ('{board.key}') deleted successfully.")


if __name__ == "__main__":
    main()
