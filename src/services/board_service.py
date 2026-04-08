"""
Board service layer.

business logic for board, column, card, and label operations.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database import Database
    from src.models import Board, Card, Column, Label


class BoardService:
    """Orchestrates board operations through the database layer."""

    def __init__(self, db: Database) -> None:  # noqa: D107
        self._db = db

    # ── Board ─────────────────────────────────────────────────────────

    def load_board(self, key: str) -> Board | None:
        """Fetch board by key, update last_login. Relationships auto-load."""
        board = self._db.get_board_by_key(key)
        if board is None:
            return None
        self._db.update_board_last_login(board.id)  # type: ignore[arg-type]
        return board

    def get_all_boards(self) -> list[Board]:
        """Return all boards."""
        return self._db.get_all_boards()

    # ── Columns ───────────────────────────────────────────────────────

    def add_column(self, board_id: int) -> Column | str:
        """Create a new column with unique default name at the end of the board."""
        existing = self._db.get_columns(board_id)
        name = "New Column"
        names = {c.name for c in existing}
        if name in names:
            i = 2
            while f"{name} {i}" in names:
                i += 1
            name = f"{name} {i}"
        position = len(existing)
        return self._db.create_column(board_id, name, position)

    def rename_column(self, board_id: int, column_id: int, name: str) -> str | None:
        """Rename a column; return error string if duplicate, None on success."""
        existing = self._db.get_columns(board_id)
        for col in existing:
            if col.id != column_id and col.name == name:
                return f"Column name '{name}' already exists"
        self._db.update_column_name(column_id, name)
        return None

    def reorder_columns(self, column_ids: list[int]) -> None:
        """Reorder columns based on the provided ID list."""
        positions = [(col_id, idx) for idx, col_id in enumerate(column_ids)]
        self._db.update_column_positions(positions)

    def delete_column(self, column_id: int) -> None:
        """Delete a column and all its cards."""
        self._db.delete_column(column_id)

    # ── Cards ─────────────────────────────────────────────────────────

    def add_card(self, column_id: int, title: str) -> Card:
        """Create a new card at the end of the column."""
        existing = self._db.get_cards(column_id)
        position = len(existing)
        return self._db.create_card(column_id, title, position)

    def edit_card_title(self, card_id: int, title: str) -> None:
        """Update a card's title."""
        self._db.update_card_title(card_id, title)

    def toggle_card_completed(self, card_id: int, *, is_completed: bool) -> None:
        """Set a card's completion status."""
        self._db.update_card_completed(card_id, is_completed=is_completed)

    def toggle_card_template(self, card_id: int, *, is_template: bool) -> None:
        """Set a card's template flag."""
        self._db.update_card_template(card_id, is_template=is_template)

    def delete_card(self, card_id: int) -> None:
        """Delete a card."""
        self._db.delete_card(card_id)

    def move_card(self, card_id: int, target_column_id: int, position: int) -> None:
        """Move a card to a target column at the given position."""
        self._db.move_card(card_id, target_column_id, position)

    def card_count(self, column_id: int) -> int:
        """Return the number of cards in a column."""
        return len(self._db.get_cards(column_id))

    def set_card_label(self, card_id: int, label_id: int | None) -> None:
        """Assign or remove a label on a card."""
        self._db.update_card_label(card_id, label_id)

    def bulk_set_label(self, card_ids: list[int], label_id: int | None) -> None:
        """Assign or remove a label on multiple cards at once."""
        self._db.bulk_set_label(card_ids, label_id)

    def bulk_set_template(self, card_ids: list[int], *, is_template: bool) -> None:
        """Set template flag on multiple cards at once."""
        self._db.bulk_set_template(card_ids, is_template=is_template)

    # ── Labels ────────────────────────────────────────────────────────

    def get_labels(self) -> list[Label]:
        """Return all global labels."""
        return self._db.get_labels()

    def validate_label(
        self,
        name: str,
        color: str,
        exclude_label_id: int | None = None,
    ) -> str | None:
        """Return error message if name or color is duplicate, else None."""
        labels = self._db.get_labels()
        for lbl in labels:
            if lbl.id == exclude_label_id:
                continue
            if lbl.name == name:
                return f"Label name '{name}' already exists"
            if lbl.color.lower() == color.lower():
                return f"Label color '{color}' already in use"
        return None

    def create_label(self, name: str, color: str) -> Label | str:
        """Create a new label. Return Label on success, error string on failure."""
        error = self.validate_label(name, color)
        if error:
            return error
        return self._db.create_label(name, color)

    def update_label(self, label_id: int, name: str, color: str) -> str | None:
        """Update a label. Return error string on failure, None on success."""
        error = self.validate_label(name, color, exclude_label_id=label_id)
        if error:
            return error
        self._db.update_label(label_id, name, color)
        return None

    def delete_label(self, label_id: int) -> None:
        """Delete a label and clear it from all cards."""
        self._db.delete_label(label_id)

    # ── Bulk delete ───────────────────────────────────────────────────

    def sort_cards(self, board_id: int, labels: list[Label]) -> None:
        """Sort cards: uncompleted first, then completed, by label then title."""
        label_map = {lb.id: (lb.name or "") for lb in labels}
        columns = self._db.get_columns(board_id)
        for col in columns:
            cards = self._db.get_cards(col.id)  # type: ignore[arg-type]

            def sort_key(c: Card) -> tuple[bool, str, str]:
                return (
                    c.is_completed,
                    label_map.get(c.label_id, "") if c.label_id else "",  # type: ignore[arg-type]
                    c.title.lower(),
                )

            cards.sort(key=sort_key)
            positions = [(c.id, idx) for idx, c in enumerate(cards)]
            self._db.update_card_positions(positions)  # type: ignore[arg-type]

    def delete_completed_cards(self, board_id: int) -> int:
        """Delete all completed non-template cards."""
        return self._db.delete_completed_non_template_cards(board_id)

    def delete_all_cards(self, board_id: int) -> int:
        """Delete all non-template cards."""
        return self._db.delete_all_non_template_cards(board_id)

    # ── Board management ──────────────────────────────────────────────

    def rename_board(self, board_id: int, name: str) -> None:
        """Rename the board."""
        self._db.update_board_name(board_id, name)

    def create_board(self, name: str, key: str) -> str | None:
        """Create a new board. Return error string on failure, None on success."""
        error = self.validate_board_key(key)
        if error:
            return error
        if self._db.board_key_exists(key):
            return "Board key already in use"
        self._db.add_board(key, name)
        return None

    _KEY_PATTERN = re.compile(r"^[a-zA-Z0-9._~-]+$")

    def validate_board_key(self, key: str) -> str | None:
        """Return an error message if the key is invalid, or None if valid."""
        if not key:
            return "Board key must not be empty"
        if not self._KEY_PATTERN.match(key):
            return "Board key contains invalid characters"
        return None

    def update_board_key(self, board_id: int, new_key: str) -> str | None:
        """Validate and update the board key."""
        error = self.validate_board_key(new_key)
        if error:
            return error
        if self._db.board_key_exists(new_key, exclude_board_id=board_id):
            return "Board key already in use"
        self._db.update_board_key(board_id, new_key)
        return None
