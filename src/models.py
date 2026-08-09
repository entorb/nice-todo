"""
SQLModel definitions for the Nice TODO.

Uses Relationship() for parent-child associations with cascade deletes
so Board.columns and Column.cards load and delete automatically.
"""

from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    """Return current time as naive UTC datetime (safe for SQLite storage)."""
    return datetime.now(tz=UTC).replace(tzinfo=None)


class Label(SQLModel, table=True):
    """A global tag with name and color, shared across all boards."""

    __tablename__ = "label"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(default="", nullable=False)
    color: str = Field(default="#cccccc", nullable=False)


class Card(SQLModel, table=True):
    """A task item within a column."""

    __tablename__ = "card"

    id: int | None = Field(default=None, primary_key=True)
    column_id: int = Field(
        foreign_key="column_.id", ondelete="CASCADE", nullable=False, index=True
    )
    title: str = Field(default="", nullable=False)
    # ponytail: not UNIQUE(column_id, position) — the swap-based reorder writes
    # positions one-by-one in a single txn, which a unique constraint would reject.
    # Duplicate positions are possible after concurrent writes; order_by(position)
    # alone is then non-deterministic. Upgrade path: deferrable unique constraint
    # + batch position assignment (single UPDATE ... CASE).
    position: int = Field(default=0, nullable=False)
    is_repeat: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    label_id: int | None = Field(
        default=None, foreign_key="label.id", ondelete="SET NULL", index=True
    )
    prio: bool | None = Field(default=None, nullable=True)
    date_created: datetime = Field(default_factory=utcnow, nullable=False)
    date_completed: datetime | None = Field(default=None, nullable=True)

    @property
    def is_completed(self) -> bool:
        """Card is completed when date_completed is set."""
        return self.date_completed is not None


class Column(SQLModel, table=True):
    """A named vertical list within a board."""

    __tablename__ = "column_"

    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(
        foreign_key="board.id", ondelete="CASCADE", nullable=False, index=True
    )
    name: str = Field(default="", nullable=False)
    position: int = Field(default=0, nullable=False)

    cards: list[Card] = Relationship(
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Card.position"},
    )


class Board(SQLModel, table=True):
    """The top-level entity containing columns and labels."""

    __tablename__ = "board"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, nullable=False, default="", index=True)
    name: str = Field(default="", nullable=False)
    last_login: datetime | None = Field(default=None, nullable=True)

    columns: list[Column] = Relationship(
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Column.position"},
    )
