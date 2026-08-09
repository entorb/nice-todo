from datetime import UTC, datetime

from src.models import Board, Card, Column, Label
from src.services.export_service import export


def _make_board(name: str, columns: list[Column]) -> Board:
    board = Board(id=1, key="test", name=name)
    board.columns = columns
    return board


def _make_column(name: str, cards: list[Card]) -> Column:
    col = Column(id=1, board_id=1, name=name)
    col.cards = cards
    return col


def _make_card(
    title: str,
    *,
    is_completed: bool = False,
    label_id: int | None = None,
    prio: bool | None = None,
) -> Card:
    return Card(
        id=1,
        column_id=1,
        title=title,
        label_id=label_id,
        prio=prio,
        date_completed=datetime.now(tz=UTC).replace(tzinfo=None)
        if is_completed
        else None,
    )


def _make_label(name: str, label_id: int = 1) -> Label:
    return Label(id=label_id, name=name)


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


class TestExportHtml:
    def test_html_full(self):
        board = _make_board(
            "My Board",
            [
                _make_column(
                    "To Do",
                    [_make_card("Task 1"), _make_card("Done", is_completed=True)],
                ),
            ],
        )
        result = export(board, [], fmt="html")
        assert "<h2>My Board</h2>" in result
        assert "<h3>To Do</h3>" in result
        assert '<li><input type="checkbox" disabled> Task 1</li>' in result
        assert '<li><input type="checkbox" checked disabled> Done</li>' in result

    def test_html_completed_only(self):
        board = _make_board(
            "Board",
            [
                _make_column(
                    "Col",
                    [_make_card("Done", is_completed=True), _make_card("Todo")],
                ),
            ],
        )
        result = export(board, [], fmt="html", completed_only=True)
        assert '<input type="checkbox" checked disabled>' in result
        assert "Todo" not in result

    def test_html_escapes_title_and_column(self):
        board = _make_board(
            "B <script>",
            [_make_column("C & D", [_make_card("<b>x</b>", is_completed=True)])],
        )
        result = export(board, [], fmt="html")
        assert "&lt;b&gt;x&lt;/b&gt;" in result
        assert "B &lt;script&gt;" in result
        assert "C &amp; D" in result


class TestExportLabelsAndPrio:
    def test_markdown_label(self):
        board = _make_board(
            "Board", [_make_column("Col", [_make_card("T", label_id=1)])]
        )
        result = export(board, [_make_label("Work")])
        assert "- [ ] T (Work)" in result

    def test_markdown_prio_marker(self):
        board = _make_board(
            "Board", [_make_column("Col", [_make_card("T", prio=True)])]
        )
        result = export(board, [])
        assert "- [ ] T ⚑" in result

    def test_markdown_prio_false_no_marker(self):
        board = _make_board(
            "Board", [_make_column("Col", [_make_card("T", prio=False)])]
        )
        result = export(board, [])
        assert "- [ ] T" in result
        assert "⚑" not in result

    def test_markdown_label_and_prio_completed_only(self):
        board = _make_board(
            "Board",
            [
                _make_column(
                    "Col", [_make_card("T", is_completed=True, label_id=1, prio=True)]
                )
            ],
        )
        result = export(board, [_make_label("Work")], completed_only=True)
        assert "- T (Work) ⚑" in result

    def test_html_label_and_prio(self):
        board = _make_board(
            "Board",
            [_make_column("Col", [_make_card("T", label_id=1, prio=True)])],
        )
        result = export(board, [_make_label("Work")], fmt="html")
        assert "<em>(Work)</em>" in result
        assert 'title="Important">⚑</span>' in result

    def test_html_label_missing_no_suffix(self):
        board = _make_board(
            "Board",
            [_make_column("Col", [_make_card("T", label_id=99)])],
        )
        result = export(board, [], fmt="html")
        assert "<em>" not in result


class TestExportTxt:
    def test_txt_full(self):
        board = _make_board(
            "My Board",
            [
                _make_column(
                    "To Do",
                    [_make_card("Task 1"), _make_card("Done", is_completed=True)],
                ),
            ],
        )
        result = export(board, [], fmt="txt")
        assert result == "To Do\n[ ] Task 1\n[x] Done\n"

    def test_txt_label_and_prio(self):
        board = _make_board(
            "Board",
            [_make_column("Col", [_make_card("T", label_id=1, prio=True)])],
        )
        result = export(board, [_make_label("Work")], fmt="txt")
        assert result == "Col\n[ ] T (Work) *\n"

    def test_txt_prio_false_no_marker(self):
        board = _make_board(
            "Board",
            [_make_column("Col", [_make_card("T", label_id=1, prio=False)])],
        )
        result = export(board, [_make_label("Work")], fmt="txt")
        assert result == "Col\n[ ] T (Work)\n"
        assert "*" not in result

    def test_txt_completed_only(self):
        board = _make_board(
            "Board",
            [
                _make_column(
                    "Col",
                    [_make_card("Done", is_completed=True), _make_card("Todo")],
                ),
            ],
        )
        result = export(board, [], fmt="txt", completed_only=True)
        assert result == "Col\nDone\n"
