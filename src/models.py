"""
SQLModel definitions for the Nice TODO.

Uses Relationship() for parent-child associations with cascade deletes
so Board.columns and Column.cards load and delete automatically.
"""

from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class Label(SQLModel, table=True):
    """A global tag with name and color, shared across all boards."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(default="", nullable=False)
    color: str = Field(default="#cccccc", nullable=False)


class Card(SQLModel, table=True):
    """A task item within a column."""

    id: int | None = Field(default=None, primary_key=True)
    column_id: int = Field(foreign_key="column_.id", nullable=False)
    title: str = Field(default="", nullable=False)
    position: int = Field(default=0, nullable=False)
    is_template: bool = Field(default=False, nullable=False)
    label_id: int | None = Field(default=None, foreign_key="label.id")
    prio: bool | None = Field(default=None, nullable=True)
    date_created: datetime = Field(default_factory=datetime.now, nullable=False)
    date_completed: datetime | None = Field(default=None, nullable=True)

    @property
    def is_completed(self) -> bool:
        """Card is completed when date_completed is set."""
        return self.date_completed is not None


class Column(SQLModel, table=True):
    """A named vertical list within a board."""

    __tablename__ = "column_"

    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="board.id", nullable=False)
    name: str = Field(default="", nullable=False)
    position: int = Field(default=0, nullable=False)

    cards: list[Card] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Board(SQLModel, table=True):
    """The top-level entity containing columns and labels."""

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, nullable=False, default="")
    name: str = Field(default="", nullable=False)
    last_login: str = Field(default="", nullable=False)

    columns: list[Column] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
