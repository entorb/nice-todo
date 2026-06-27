from datetime import UTC, datetime

from src.models import Board, Card, Column
from src.services.export_service import export


def _make_board(name: str, columns: list[Column]) -> Board:
    board = Board(id=1, key="test", name=name)
    board.columns = columns
    return board


def _make_column(name: str, cards: list[Card]) -> Column:
    col = Column(id=1, board_id=1, name=name)
    col.cards = cards
    return col


def _make_card(title: str, *, is_completed: bool = False) -> Card:
    return Card(
        id=1,
        column_id=1,
        title=title,
        date_completed=datetime.now(tz=UTC).replace(tzinfo=None)
        if is_completed
        else None,
    )


class TestExportAll:
    def test_board_with_cards(self):
        board = _make_board(
            "My Board",
            [
                _make_column("To Do", [_make_card("Task 1"), _make_card("Task 2")]),
                _make_column("Done", [_make_card("Task 3", is_completed=True)]),
            ],
        )
        result = export(board, [])
        expected = (
            "## My Board\n\n### To Do\n- [ ] Task 1\n- [ ] Task 2\n"
            "\n### Done\n- [x] Task 3\n"
        )
        assert result == expected

    def test_omits_empty_columns(self):
        board = _make_board(
            "Board",
            [
                _make_column("Empty", []),
                _make_column("Has Cards", [_make_card("A")]),
            ],
        )
        result = export(board, [])
        assert "### Empty" not in result
        assert "### Has Cards" in result

    def test_board_with_no_columns(self):
        board = _make_board("Empty Board", [])
        result = export(board, [])
        assert result == "## Empty Board\n"

    def test_board_with_all_empty_columns(self):
        board = _make_board(
            "Board",
            [
                _make_column("Col1", []),
                _make_column("Col2", []),
            ],
        )
        result = export(board, [])
        assert result == "## Board\n"


class TestExportCompleted:
    def test_only_completed_cards(self):
        board = _make_board(
            "My Board",
            [
                _make_column(
                    "To Do",
                    [
                        _make_card("Incomplete", is_completed=False),
                        _make_card("Done task", is_completed=True),
                    ],
                ),
            ],
        )
        result = export(board, [], completed_only=True)
        assert "- Done task" in result
        assert "- Incomplete" not in result

    def test_omits_columns_with_no_completed(self):
        board = _make_board(
            "Board",
            [
                _make_column("All Incomplete", [_make_card("A", is_completed=False)]),
                _make_column("Has Done", [_make_card("B", is_completed=True)]),
            ],
        )
        result = export(board, [], completed_only=True)
        assert "### All Incomplete" not in result
        assert "### Has Done" in result

    def test_empty_board(self):
        board = _make_board("Board", [])
        result = export(board, [], completed_only=True)
        assert result == "## Board\n"

    def test_no_completed_cards_anywhere(self):
        board = _make_board(
            "Board",
            [
                _make_column("Col", [_make_card("X", is_completed=False)]),
            ],
        )
        result = export(board, [], completed_only=True)
        assert result == "## Board\n"
