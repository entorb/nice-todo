"""
SQLModel-based database layer for the Nice TODO.

all text inputs are stripped of white spaces prior to insert/update
"""

from datetime import datetime
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from src.models import Board, Card, Column, Label


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
        """Create all tables if they don't exist."""
        SQLModel.metadata.create_all(self._engine)

    def session(self) -> Session:
        """Create a new database session."""
        return Session(self._engine)

    # Board

    def get_board_by_key(self, key: str) -> Board | None:
        """Load board with all relationships, sorted by position."""
        with self.session() as s:
            board = s.exec(select(Board).where(Board.key == key)).first()
            if board is None:
                return None
            # Eagerly access relationships before session closes
            board.columns.sort(key=lambda c: c.position)
            for col in board.columns:
                col.cards.sort(key=lambda c: c.position)
            return board

    def get_all_boards(self) -> list[Board]:
        """Return all boards (lightweight, no relationships eagerly loaded)."""
        with self.session() as s:
            return list(s.exec(select(Board).order_by(Board.name)).all())

    def add_board(self, key: str, name: str) -> Board:
        """Create a new board."""
        with self.session() as s:
            board = Board(key=key.strip().lower(), name=name.strip())
            s.add(board)
            s.commit()
            s.refresh(board)
            return board

    def update_board_last_login(self, board_id: int) -> None:
        """Update the board's last login timestamp."""
        with self.session() as s:
            if board := s.get(Board, board_id):
                board.last_login = datetime.now().isoformat()  # noqa: DTZ005
                s.add(board)
                s.commit()

    def update_board_name(self, board_id: int, name: str) -> None:
        """Rename the board."""
        with self.session() as s:
            if board := s.get(Board, board_id):
                board.name = name.strip()
                s.add(board)
                s.commit()

    def update_board_key(self, board_id: int, new_key: str) -> None:
        """Change the board's URL key."""
        with self.session() as s:
            if board := s.get(Board, board_id):
                board.key = new_key.strip()
                s.add(board)
                s.commit()

    def board_key_exists(self, key: str, exclude_board_id: int | None = None) -> bool:
        """Check if a board key is already taken."""
        with self.session() as s:
            stmt = select(Board).where(Board.key == key)
            if exclude_board_id is not None:
                stmt = stmt.where(Board.id != exclude_board_id)
            return s.exec(stmt).first() is not None

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

    def create_column(self, board_id: int, name: str, position: int) -> Column:
        """Create a new column."""
        with self.session() as s:
            col = Column(board_id=board_id, name=name.strip(), position=position)
            s.add(col)
            s.commit()
            s.refresh(col)
            return col

    def update_column_name(self, column_id: int, name: str) -> None:
        """Rename a column."""
        with self.session() as s:
            if col := s.get(Column, column_id):
                col.name = name.strip()
                s.add(col)
                s.commit()

    def update_column_positions(self, positions: list[tuple[int, int]]) -> None:
        """Batch-update column positions."""
        with self.session() as s:
            for col_id, pos in positions:
                if col := s.get(Column, col_id):
                    col.position = pos
                    s.add(col)
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
            card = Card(column_id=column_id, title=title.strip(), position=position)
            s.add(card)
            s.commit()
            s.refresh(card)
            return card

    def update_card_title(self, card_id: int, title: str) -> None:
        """Update a card's title."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.title = title.strip()
                s.add(card)
                s.commit()

    def update_card_completed(self, card_id: int, *, is_completed: bool) -> None:
        """Toggle a card's completion status via date_completed."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.date_completed = datetime.now() if is_completed else None  # noqa: DTZ005
                s.add(card)
                s.commit()

    def update_card_template(self, card_id: int, *, is_template: bool) -> None:
        """Toggle a card's template flag."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.is_template = is_template
                s.add(card)
                s.commit()

    def update_card_label(self, card_id: int, label_id: int | None) -> None:
        """Set or clear a card's label."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.label_id = label_id
                s.add(card)
                s.commit()

    def move_card(self, card_id: int, target_column_id: int, position: int) -> None:
        """Move a card to a different column/position."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                card.column_id = target_column_id
                card.position = position
                s.add(card)
                s.commit()

    def update_card_positions(self, positions: list[tuple[int, int]]) -> None:
        """Batch-update card positions."""
        with self.session() as s:
            for card_id, pos in positions:
                if card := s.get(Card, card_id):
                    card.position = pos
                    s.add(card)
            s.commit()

    def delete_card(self, card_id: int) -> None:
        """Delete a single card."""
        with self.session() as s:
            if card := s.get(Card, card_id):
                s.delete(card)
                s.commit()

    def delete_completed_non_template_cards(self, board_id: int) -> int:
        """Delete completed non-template cards across all board columns."""
        with self.session() as s:
            col_ids = [
                c.id
                for c in s.exec(select(Column).where(Column.board_id == board_id)).all()
            ]
            if not col_ids:
                return 0
            cards = s.exec(
                select(Card)
                .where(Card.column_id.in_(col_ids))  # type: ignore[union-attr]
                .where(Card.date_completed.is_not(None))  # type: ignore[union-attr]
                .where(Card.is_template == False)  # noqa: E712
            ).all()
            for card in cards:
                s.delete(card)
            s.commit()
            return len(cards)

    def delete_all_non_template_cards(self, board_id: int) -> int:
        """Delete all non-template cards across all board columns."""
        with self.session() as s:
            col_ids = [
                c.id
                for c in s.exec(select(Column).where(Column.board_id == board_id)).all()
            ]
            if not col_ids:
                return 0
            cards = s.exec(
                select(Card)
                .where(Card.column_id.in_(col_ids))  # type: ignore[union-attr]
                .where(Card.is_template == False)  # noqa: E712
            ).all()
            for card in cards:
                s.delete(card)
            s.commit()
            return len(cards)

    def bulk_set_label(self, card_ids: list[int], label_id: int | None) -> None:
        """Set label on multiple cards at once."""
        with self.session() as s:
            for card_id in card_ids:
                if card := s.get(Card, card_id):
                    card.label_id = label_id
                    s.add(card)
            s.commit()

    def bulk_set_template(self, card_ids: list[int], *, is_template: bool) -> None:
        """Set template flag on multiple cards at once."""
        with self.session() as s:
            for card_id in card_ids:
                if card := s.get(Card, card_id):
                    card.is_template = is_template
                    s.add(card)
            s.commit()

    # Labels

    def get_labels(self) -> list[Label]:
        """Get all labels."""
        with self.session() as s:
            return list(s.exec(select(Label).order_by(Label.name)).all())

    def create_label(self, name: str, color: str) -> Label:
        """Create a new label."""
        with self.session() as s:
            label = Label(name=name.strip(), color=color.strip().lower())
            s.add(label)
            s.commit()
            s.refresh(label)
            return label

    def update_label(self, label_id: int, name: str, color: str) -> None:
        """Update a label's name and color."""
        with self.session() as s:
            if label := s.get(Label, label_id):
                label.name = name.strip()
                label.color = color.strip().lower()
                s.add(label)
                s.commit()

    def delete_label(self, label_id: int) -> None:
        """Delete a label and clear it from all cards that had it."""
        with self.session() as s:
            # Clear label_id on cards (SQLite ON DELETE SET NULL would also work,
            # but we do it explicitly for clarity)
            for card in s.exec(select(Card).where(Card.label_id == label_id)).all():
                card.label_id = None
                s.add(card)
            if label := s.get(Label, label_id):
                s.delete(label)
            s.commit()
