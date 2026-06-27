"""
SQLModel-based database layer for the Nice TODO.

all text inputs are stripped of white spaces prior to insert/update
"""

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import selectinload  # type: ignore[attr-defined]
from sqlmodel import Session, SQLModel, create_engine, select, update

from src.models import Board, Card, Column, Label
from src.services.sort import card_sort_by_date, card_sort_by_prio_label_name

_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9._~-]+$")


def _utcnow() -> datetime:
    """Return current UTC time as naive datetime (safe for SQLite storage)."""
    return datetime.now(tz=UTC).replace(tzinfo=None)


def _clean_title(title: str) -> str:
    """Normalize title by stripping whitespace and collapsing multiple spaces."""
    # CRLF to LF
    title = title.replace("\r\n", "\n")
    # drop multiple spaces, but keep line breaks
    title = re.sub(r"[ \t]+", " ", title)
    # strip
    title = title.strip()
    return title


class Database:
    """SQLite database access using SQLModel."""

    def __init__(self, db_path: Path) -> None:
        """Initialize database engine."""
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

    def init(self) -> None:
        """Create all tables if they don't exist, and run migrations."""
        SQLModel.metadata.create_all(self._engine)
        self._migrate()

    def _migrate(self) -> None:
        """Add missing columns to existing tables based on SQLModel metadata."""
        db_path = str(self._engine.url).replace("sqlite:///", "")
        with sqlite3.connect(db_path) as conn:
            for table in SQLModel.metadata.sorted_tables:
                existing = {
                    row[1] for row in conn.execute(f"PRAGMA table_info({table.name})")
                }
                if not existing:
                    continue
                for col in table.columns:
                    if col.name not in existing:
                        col_type = col.type.compile(dialect=self._engine.dialect)
                        conn.execute(
                            f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
                        )
            # Data migration: convert empty last_login strings to NULL
            conn.execute("UPDATE board SET last_login = NULL WHERE last_login = ''")

    def session(self) -> Session:
        """Create a new database session."""
        return Session(self._engine)

    # Board

    def get_board_by_key(self, key: str) -> Board | None:
        """Load board with all relationships eagerly loaded, update last_login."""
        with self.session() as sess:
            board = sess.exec(
                select(Board)
                .where(Board.key == key)
                .options(
                    selectinload(Board.columns).selectinload(Column.cards),
                )
            ).first()
        if board is not None and board.id is not None:
            with self.session() as sess:
                if b := sess.get(Board, board.id):
                    b.last_login = _utcnow()
                    sess.commit()
        return board

    def get_all_boards(self) -> list[Board]:
        """Return all boards (lightweight, no relationships eagerly loaded)."""
        with self.session() as s:
            return list(s.exec(select(Board).order_by(Board.name)).all())

    def validate_board_key(self, key: str, exclude_id: int | None = None) -> str | None:
        """Return error message if key is invalid, None if valid."""
        if not key:
            return "Board key must not be empty"
        if not _KEY_PATTERN.match(key):
            return "Board key contains invalid characters"
        existing = self.get_board_by_key(key)
        if existing is not None and (exclude_id is None or existing.id != exclude_id):
            return "Board key must be unique"
        return None

    def add_board(self, key: str, name: str) -> Board | str:
        """Create a new board. Return Board on success, error string on failure."""
        key_clean = key.strip().lower()
        error = self.validate_board_key(key_clean)
        if error:
            return error
        with self.session() as s:
            board = Board(key=key_clean, name=name.strip())
            s.add(board)
            s.commit()
            s.refresh(board)
            return board

    def update_board_name(self, board_id: int, name: str) -> None:
        """Rename the board."""
        with self.session() as s:
            if board := s.get(Board, board_id):
                board.name = name.strip()
                s.commit()

    def update_board_key(self, board_id: int, new_key: str) -> str | None:
        """Change the board's URL key. Return error string or None."""
        key_clean = new_key.strip()
        error = self.validate_board_key(key_clean, exclude_id=board_id)
        if error:
            return error
        with self.session() as s:
            if board := s.get(Board, board_id):
                board.key = key_clean
                s.commit()
        return None

    def delete_board(self, board_id: int) -> None:
        """Delete board and all associated data (cascades via relationships)."""
        with self.session() as s:
            if board := s.get(Board, board_id):
                s.delete(board)
                s.commit()

    # Columns

    def get_columns(self, board_id: int) -> list[Column]:
        """Get columns for a board, ordered by position."""
        with self.session() as s:
            return list(
                s.exec(
                    select(Column)
                    .where(Column.board_id == board_id)
                    .order_by(Column.position)
                ).all()
            )

    def create_column(self, board_id: int) -> Column:
        """Create a new column with unique default name at end."""
        existing = self.get_columns(board_id)
        name = "New Column"
        names = {c.name for c in existing}
        if name in names:
            i = 2
            while f"{name} {i}" in names:
                i += 1
            name = f"{name} {i}"
        with self.session() as s:
            col = Column(board_id=board_id, name=name, position=len(existing))
            s.add(col)
            s.commit()
            s.refresh(col)
            return col

    def update_column_name(
        self, column_id: int, name: str, board_id: int
    ) -> str | None:
        """Rename a column. Return error string if duplicate, None on success."""
        existing = self.get_columns(board_id)
        for col in existing:
            if col.id != column_id and col.name == name:
                return f"Column name '{name}' already exists"
        with self.session() as s:
            if col := s.get(Column, column_id):
                col.name = name.strip()
                s.commit()
        return None

    def update_column_positions(self, positions: list[tuple[int, int]]) -> None:
        """Batch-update column positions."""
        with self.session() as s:
            for col_id, pos in positions:
                s.exec(update(Column).where(Column.id == col_id).values(position=pos))
            s.commit()

    def delete_column(self, column_id: int) -> None:
        """Delete column and its cards (cascades via relationship)."""
        with self.session() as s:
            if col := s.get(Column, column_id):
                s.delete(col)
                s.commit()

    # Cards

    def get_cards(self, column_id: int) -> list[Card]:
        """Get cards for a column, ordered by position."""
        with self.session() as s:
            return list(
                s.exec(
                    select(Card)
                    .where(Card.column_id == column_id)
                    .order_by(Card.position)
                ).all()
            )

    def create_card(self, column_id: int, title: str, position: int) -> Card:
        """Create a new card."""
        with self.session() as s:
            title = _clean_title(title)
            card = Card(column_id=column_id, title=title, position=position)
            s.add(card)
            s.commit()
            s.refresh(card)
            return card

    def update_card_title(self, card_id: int, title: str) -> None:
        """Update a card's title."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.title = _clean_title(title)
                s.commit()

    def update_card_completed(self, card_id: int, *, is_completed: bool) -> None:
        """Toggle a card's completion status via date_completed."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.date_completed = _utcnow() if is_completed else None
                s.commit()

    def update_card_repeat(self, card_id: int, *, is_repeat: bool) -> None:
        """Toggle a card's repeat flag."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.is_repeat = is_repeat
                s.commit()

    def update_card_prio(self, card_id: int, prio: bool | None) -> None:  # noqa: FBT001
        """Set a card's prio flag (True, False, or None)."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.prio = prio
                s.commit()

    def update_card_label(self, card_id: int, label_id: int | None) -> None:
        """Set or clear a card's label."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.label_id = label_id
                s.commit()

    def move_card(self, card_id: int, target_column_id: int, position: int) -> None:
        """Move a card to a different column/position."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.column_id = target_column_id
                card.position = position
                s.commit()

    def update_card_positions(self, positions: list[tuple[int, int]]) -> None:
        """Batch-update card positions."""
        with self.session() as s:
            for card_id, pos in positions:
                s.exec(update(Card).where(Card.id == card_id).values(position=pos))
            s.commit()

    def copy_card(self, card_id: int, target_column_id: int, position: int) -> Card:
        """Copy a card to a target column in one session."""
        with self.session() as s:
            original = s.get(Card, card_id)
            if original is None:
                msg = f"Card {card_id} not found"
                raise ValueError(msg)
            new_card = Card(
                column_id=target_column_id,
                title=original.title,
                position=position,
                label_id=original.label_id,
                is_repeat=original.is_repeat,
                prio=original.prio,
            )
            s.add(new_card)
            s.commit()
            s.refresh(new_card)
            return new_card

    def delete_card(self, card_id: int) -> None:
        """Delete a single card."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                s.delete(card)
                s.commit()

    def _delete_cards_where(
        self,
        board_id: int,
        *,
        extra_conditions: list | None = None,
        reset_repeats: bool = False,
    ) -> int:
        """Delete non-repeat cards matching conditions, optionally reset repeats."""
        with self.session() as s:
            col_ids = [
                c.id
                for c in s.exec(select(Column).where(Column.board_id == board_id)).all()
            ]
            if not col_ids:
                return 0

            conditions = [Card.column_id.in_(col_ids)]  # type: ignore[union-attr]
            conditions.append(Card.is_repeat.is_(False))
            if extra_conditions:
                conditions.extend(extra_conditions)

            cards = s.exec(select(Card).where(*conditions)).all()
            for card in cards:
                s.delete(card)

            if reset_repeats:
                s.exec(
                    update(Card)
                    .where(Card.column_id.in_(col_ids))  # type: ignore[union-attr]
                    .where(Card.is_repeat.is_(True))
                    .values(date_completed=None),
                )

            s.commit()
            return len(cards)

    def delete_completed_non_repeat_cards(self, board_id: int) -> int:
        """Delete completed non-repeat cards and unset date_completed on repeats."""
        return self._delete_cards_where(
            board_id,
            extra_conditions=[Card.date_completed.is_not(None)],  # type: ignore[union-attr]
            reset_repeats=True,
        )

    def delete_completed_non_repeat_cards_older_than(
        self, board_id: int, days: int
    ) -> int:
        """Delete completed non-repeat cards completed > `days` ago."""
        cutoff = _utcnow() - timedelta(days=days)
        return self._delete_cards_where(
            board_id,
            extra_conditions=[
                Card.date_completed.is_not(None),  # type: ignore[union-attr]
                Card.date_completed < cutoff,  # type: ignore[union-attr]
            ],
        )

    def delete_all_non_repeat_cards(self, board_id: int) -> int:
        """Delete all non-repeat cards and unset date_completed on repeats."""
        return self._delete_cards_where(
            board_id,
            reset_repeats=True,
        )

    def bulk_set_label(self, card_ids: list[int], label_id: int | None) -> None:
        """Set label on multiple cards at once."""
        with self.session() as s:
            s.exec(
                update(Card)
                .where(Card.id.in_(card_ids))  # type: ignore[union-attr]
                .values(label_id=label_id),
            )
            s.commit()

    def bulk_set_repeat(self, card_ids: list[int], *, is_repeat: bool) -> None:
        """Set repeat flag on multiple cards at once."""
        with self.session() as s:
            s.exec(
                update(Card)
                .where(Card.id.in_(card_ids))  # type: ignore[union-attr]
                .values(is_repeat=is_repeat),
            )
            s.commit()

    def bulk_set_prio(self, card_ids: list[int], prio: bool | None) -> None:  # noqa: FBT001
        """Set prio flag on multiple cards at once."""
        with self.session() as s:
            s.exec(
                update(Card)
                .where(Card.id.in_(card_ids))  # type: ignore[union-attr]
                .values(prio=prio),
            )
            s.commit()

    # Sorting

    def sort_cards_by_prio_label_name(self, board: Board, labels: list[Label]) -> None:
        """Sort cards per column: completed, prio, label name, title."""
        label_map: dict[int | None, str] = {lb.id: (lb.name or "") for lb in labels}
        key_fn = card_sort_by_prio_label_name(label_map)
        for col in board.columns:
            cards = sorted(col.cards, key=key_fn)
            positions = [(c.id, idx) for idx, c in enumerate(cards)]
            self.update_card_positions(positions)  # type: ignore[arg-type]

    def sort_cards_by_date(self, board: Board) -> None:
        """Sort by date (incomplete: date_created, completed: date_completed)."""
        key_fn = card_sort_by_date()
        for col in board.columns:
            cards = sorted(col.cards, key=key_fn)
            positions = [(c.id, idx) for idx, c in enumerate(cards)]
            self.update_card_positions(positions)  # type: ignore[arg-type]

    # Labels

    def _validate_label(
        self,
        name: str,
        color: str,
        exclude_label_id: int | None = None,
    ) -> str | None:
        """Return error message if name or color is duplicate, else None."""
        labels = self.get_labels()
        for lbl in labels:
            if lbl.id == exclude_label_id:
                continue
            if lbl.name == name:
                return f"Label name '{name}' already exists"
            if lbl.color.lower() == color.lower():
                return f"Label color '{color}' already in use"
        return None

    def get_labels(self) -> list[Label]:
        """Get all labels."""
        with self.session() as s:
            return list(s.exec(select(Label).order_by(Label.name)).all())

    def create_label(self, name: str, color: str) -> Label | str:
        """Create a new label. Return Label on success, error string on failure."""
        name_clean = name.strip()
        color_clean = color.strip().lower()
        error = self._validate_label(name_clean, color_clean)
        if error:
            return error
        with self.session() as s:
            label = Label(name=name_clean, color=color_clean)
            s.add(label)
            s.commit()
            s.refresh(label)
            return label

    def update_label(self, label_id: int, name: str, color: str) -> str | None:
        """Update a label. Return error string on failure, None on success."""
        name_clean = name.strip()
        color_clean = color.strip().lower()
        error = self._validate_label(name_clean, color_clean, exclude_label_id=label_id)
        if error:
            return error
        with self.session() as s:
            if label := s.get(Label, label_id):
                label.name = name_clean
                label.color = color_clean
                s.commit()
        return None

    def delete_label(self, label_id: int) -> None:
        """Delete a label and clear it from all cards that had it."""
        with self.session() as s:
            # Clear label_id on cards (SQLite ON DELETE SET NULL would also work,
            # but we do it explicitly for clarity)
            for card in s.exec(select(Card).where(Card.label_id == label_id)).all():
                card.label_id = None
            if label := s.get(Label, label_id):
                s.delete(label)
            s.commit()
