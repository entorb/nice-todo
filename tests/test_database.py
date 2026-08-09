from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from src.models import Board, Card, Column, Label


def _new_board(db, key: str = "test", name: str = "Board") -> Board:
    result = db.add_board(key, name)
    assert isinstance(result, Board)
    return result


def _new_column(db) -> Column:
    board = _new_board(db)
    return db.create_column(board.id)


def _new_card(db, title: str = "Card") -> Card:
    col = _new_column(db)
    return db.create_card(col.id, title, 0)


class TestBoard:
    def test_add_board(self, db):
        board = db.add_board("MyBoard", "  My Board  ")
        assert isinstance(board, Board)
        assert board.key == "myboard"
        assert board.name == "My Board"

    def test_add_board_duplicate_key(self, db):
        db.add_board("same", "One")
        result = db.add_board("SAME", "Two")
        assert result == "Board key must be unique"

    def test_add_board_invalid_key(self, db):
        result = db.add_board("bad key!", "Bad")
        assert result == "Board key contains invalid characters"

    def test_add_board_empty_key(self, db):
        result = db.add_board("", "Empty")
        assert result == "Board key must not be empty"

    def test_add_board_race_unique_violation(self, db, monkeypatch):
        """Concurrent same-key insert is caught via the IntegrityError backstop."""
        db.add_board("same", "One")
        monkeypatch.setattr(
            db, "validate_board_key", lambda _key, _exclude_id=None: None
        )
        result = db.add_board("same", "Two")
        assert result == "Board key must be unique"

    def test_get_boards_with_columns(self, db):
        board = _new_board(db)
        db.create_column(board.id)
        boards = db.get_boards_with_columns()
        assert len(boards) == 1
        assert [c.id for c in boards[0].columns] == [
            c.id for c in db.get_columns(board.id)
        ]

    def test_rename_board(self, db):
        board = _new_board(db)
        db.update_board_name(board.id, "  New Name  ")
        assert db.get_board_by_key("test").name == "New Name"

    def test_update_board_key(self, db):
        board = _new_board(db)
        error = db.update_board_key(board.id, "new-key")
        assert error is None
        assert db.get_board_by_key("new-key") is not None
        assert db.get_board_by_key("test") is None

    def test_update_board_key_duplicate(self, db):
        db.add_board("a", "A")
        board_b = db.add_board("b", "B")
        error = db.update_board_key(board_b.id, "a")
        assert error == "Board key must be unique"

    def test_update_board_key_to_own_key(self, db):
        board = _new_board(db)
        error = db.update_board_key(board.id, "test")
        assert error is None

    def test_delete_board_cascades(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        db.create_card(col.id, "Card", 0)
        db.delete_board(board.id)
        assert db.get_board_by_key("test") is None
        assert db.get_columns(board.id) == []
        assert db.get_cards(col.id) == []

    def test_get_board_by_key_missing(self, db):
        assert db.get_board_by_key("nope") is None

    def test_get_all_boards_ordered(self, db):
        db.add_board("b", "B")
        db.add_board("a", "A")
        assert [b.key for b in db.get_all_boards()] == ["a", "b"]


class TestColumn:
    def test_create_column(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        assert col.name == "New Column"
        assert col.position == 0
        cols = db.get_columns(board.id)
        assert len(cols) == 1
        assert cols[0].name == "New Column"
        assert cols[0].position == 0

    def test_create_column_unique_default_name(self, db):
        board = _new_board(db)
        db.create_column(board.id)
        col2 = db.create_column(board.id)
        assert col2.name == "New Column 2"
        assert col2.position == 1

    def test_rename_column(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        error = db.update_column_name(col.id, "  To Do  ", board.id)
        assert error is None
        assert db.get_columns(board.id)[0].name == "To Do"

    def test_rename_column_duplicate(self, db):
        board = _new_board(db)
        db.create_column(board.id)
        col2 = db.create_column(board.id)
        error = db.update_column_name(col2.id, "New Column", board.id)
        assert error == "Column name 'New Column' already exists"

    def test_update_column_positions(self, db):
        board = _new_board(db)
        c1 = db.create_column(board.id)
        c2 = db.create_column(board.id)
        c3 = db.create_column(board.id)
        db.update_column_positions([(c1.id, 2), (c2.id, 0), (c3.id, 1)])
        cols = db.get_columns(board.id)
        assert [c.id for c in cols] == [c2.id, c3.id, c1.id]
        assert [c.position for c in cols] == [0, 1, 2]

    def test_delete_column_cascades_cards(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        db.create_card(col.id, "Card", 0)
        db.delete_column(col.id)
        assert db.get_columns(board.id) == []
        assert db.get_cards(col.id) == []


class TestCard:
    def test_create_card_cleans_title(self, db):
        col = _new_column(db)
        card = db.create_card(col.id, "  Hello   World  ", 0)
        assert card.title == "Hello World"

    def test_update_card_title(self, db):
        card = _new_card(db)
        db.update_card_title(card.id, "  New   Title  ")
        assert db.get_cards(card.column_id)[0].title == "New Title"

    def test_toggle_completed(self, db):
        card = _new_card(db)
        db.update_card_completed(card.id, is_completed=True)
        reloaded = db.get_cards(card.column_id)[0]
        assert reloaded.is_completed is True
        assert reloaded.date_completed is not None
        db.update_card_completed(card.id, is_completed=False)
        assert db.get_cards(card.column_id)[0].date_completed is None

    def test_toggle_repeat(self, db):
        card = _new_card(db)
        db.update_card_repeat(card.id, is_repeat=True)
        assert db.get_cards(card.column_id)[0].is_repeat is True
        db.update_card_repeat(card.id, is_repeat=False)
        assert db.get_cards(card.column_id)[0].is_repeat is False

    def test_update_prio(self, db):
        card = _new_card(db)
        db.update_card_prio(card.id, prio=True)
        assert db.get_cards(card.column_id)[0].prio is True
        db.update_card_prio(card.id, prio=None)
        assert db.get_cards(card.column_id)[0].prio is None
        db.update_card_prio(card.id, prio=False)
        assert db.get_cards(card.column_id)[0].prio is False

    def test_set_and_clear_label(self, db):
        card = _new_card(db)
        label = db.create_label("Urgent", "#ff0000")
        assert isinstance(label, Label)
        db.update_card_label(card.id, label.id)
        assert db.get_cards(card.column_id)[0].label_id == label.id
        db.update_card_label(card.id, None)
        assert db.get_cards(card.column_id)[0].label_id is None

    def test_move_card(self, db):
        card = _new_card(db)
        orig_column_id = card.column_id
        board = db.get_board_by_key("test")
        col2 = db.create_column(board.id)
        db.move_card(card.id, col2.id, 5)
        moved = db.get_cards(col2.id)[0]
        assert moved.column_id == col2.id
        assert moved.position == 5
        assert db.get_cards(orig_column_id) == []

    def test_update_card_positions(self, db):
        col = _new_column(db)
        c1 = db.create_card(col.id, "A", 0)
        c2 = db.create_card(col.id, "B", 1)
        c3 = db.create_card(col.id, "C", 2)
        db.update_card_positions([(c1.id, 2), (c2.id, 0), (c3.id, 1)])
        cards = db.get_cards(col.id)
        assert [c.id for c in cards] == [c2.id, c3.id, c1.id]

    def test_copy_card(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        label = db.create_label("Tag", "#00ff00")
        assert isinstance(label, Label)
        card = db.create_card(col.id, "Original", 0)
        db.update_card_label(card.id, label.id)
        db.update_card_prio(card.id, prio=True)
        db.update_card_repeat(card.id, is_repeat=True)
        copy = db.copy_card(card.id, col.id, 3)
        assert copy.id != card.id
        assert copy.title == "Original"
        assert copy.label_id == label.id
        assert copy.prio is True
        assert copy.is_repeat is True
        assert copy.position == 3
        assert copy.date_completed is None

    def test_copy_card_missing(self, db):
        with pytest.raises(ValueError, match="not found"):
            db.copy_card(999, 1, 0)

    def test_delete_card(self, db):
        card = _new_card(db)
        db.delete_card(card.id)
        assert db.get_cards(card.column_id) == []

    def test_delete_completed_non_repeat_cards(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        done = db.create_card(col.id, "Done", 0)
        db.update_card_completed(done.id, is_completed=True)
        db.create_card(col.id, "Todo", 1)
        repeat_done = db.create_card(col.id, "Repeat", 2)
        db.update_card_repeat(repeat_done.id, is_repeat=True)
        db.update_card_completed(repeat_done.id, is_completed=True)
        count = db.delete_completed_non_repeat_cards(board.id)
        assert count == 1
        remaining = db.get_cards(col.id)
        assert [c.title for c in remaining] == ["Todo", "Repeat"]
        assert remaining[1].date_completed is None

    def test_delete_completed_older_than(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        old = db.create_card(col.id, "Old done", 0)
        db.update_card_completed(old.id, is_completed=True)
        with db.session() as s:
            old_card = s.get(Card, old.id)
            old_card.date_completed = datetime.now(tz=UTC).replace(
                tzinfo=None
            ) - timedelta(days=10)
            s.commit()
        recent = db.create_card(col.id, "Recent done", 1)
        db.update_card_completed(recent.id, is_completed=True)
        count = db.delete_completed_non_repeat_cards_older_than(board.id, days=5)
        assert count == 1
        assert [c.title for c in db.get_cards(col.id)] == ["Recent done"]

    def test_delete_all_non_repeat_cards(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        db.create_card(col.id, "A", 0)
        repeat_done = db.create_card(col.id, "B", 1)
        db.update_card_repeat(repeat_done.id, is_repeat=True)
        db.update_card_completed(repeat_done.id, is_completed=True)
        count = db.delete_all_non_repeat_cards(board.id)
        assert count == 1
        remaining = db.get_cards(col.id)
        assert [c.title for c in remaining] == ["B"]
        assert remaining[0].date_completed is None

    def test_bulk_set_label(self, db):
        col = _new_column(db)
        c1 = db.create_card(col.id, "A", 0)
        c2 = db.create_card(col.id, "B", 1)
        label = db.create_label("L", "#123456")
        assert isinstance(label, Label)
        db.bulk_set_label([c1.id, c2.id], label.id)
        assert {c.label_id for c in db.get_cards(col.id)} == {label.id}
        db.bulk_set_label([c1.id], None)
        cards = db.get_cards(col.id)
        assert cards[0].label_id is None
        assert cards[1].label_id == label.id

    def test_bulk_set_repeat(self, db):
        col = _new_column(db)
        c1 = db.create_card(col.id, "A", 0)
        c2 = db.create_card(col.id, "B", 1)
        db.bulk_set_repeat([c1.id, c2.id], is_repeat=True)
        assert all(c.is_repeat for c in db.get_cards(col.id))
        db.bulk_set_repeat([c1.id], is_repeat=False)
        assert db.get_cards(col.id)[0].is_repeat is False

    def test_bulk_set_prio(self, db):
        col = _new_column(db)
        c1 = db.create_card(col.id, "A", 0)
        c2 = db.create_card(col.id, "B", 1)
        db.bulk_set_prio([c1.id, c2.id], prio=True)
        assert all(c.prio is True for c in db.get_cards(col.id))
        db.bulk_set_prio([c2.id], None)
        assert db.get_cards(col.id)[1].prio is None


class TestSort:
    def test_sort_by_prio_label_name(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        label_a = db.create_label("Alpha", "#111111")
        assert isinstance(label_a, Label)
        mid = db.create_card(col.id, "Mid", 0)
        db.update_card_label(mid.id, label_a.id)
        db.update_card_prio(mid.id, None)
        high = db.create_card(col.id, "High", 1)
        db.update_card_prio(high.id, prio=True)
        low = db.create_card(col.id, "Low", 2)
        db.update_card_prio(low.id, prio=False)
        done = db.create_card(col.id, "Done", 3)
        db.update_card_completed(done.id, is_completed=True)
        board = db.get_board_by_key("test")
        db.sort_cards_by_prio_label_name(board, db.get_labels())
        assert [c.title for c in db.get_cards(col.id)] == [
            "High",
            "Mid",
            "Low",
            "Done",
        ]

    def test_sort_by_date(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        done1 = db.create_card(col.id, "Done1", 0)
        db.update_card_completed(done1.id, is_completed=True)
        db.create_card(col.id, "Todo", 1)
        done2 = db.create_card(col.id, "Done2", 2)
        db.update_card_completed(done2.id, is_completed=True)
        with db.session() as s:
            done2_card = s.get(Card, done2.id)
            done2_card.date_completed = datetime.now(tz=UTC).replace(
                tzinfo=None
            ) - timedelta(days=1)
            s.commit()
        board = db.get_board_by_key("test")
        db.sort_cards_by_date(board)
        assert [c.title for c in db.get_cards(col.id)] == [
            "Todo",
            "Done2",
            "Done1",
        ]


class TestLabel:
    def test_create_label(self, db):
        label = db.create_label("  Urgent  ", "  #FF0000  ")
        assert isinstance(label, Label)
        assert label.name == "Urgent"
        assert label.color == "#ff0000"

    def test_create_label_duplicate_name(self, db):
        db.create_label("Urgent", "#ff0000")
        result = db.create_label("Urgent", "#00ff00")
        assert result == "Label name 'Urgent' already exists"

    def test_create_label_duplicate_color(self, db):
        db.create_label("Urgent", "#ff0000")
        result = db.create_label("Later", "#FF0000")
        assert result == "Label color '#ff0000' already in use"

    def test_update_label(self, db):
        label = db.create_label("Old", "#ff0000")
        assert isinstance(label, Label)
        error = db.update_label(label.id, "New", "#00ff00")
        assert error is None
        updated = db.get_labels()[0]
        assert updated.name == "New"
        assert updated.color == "#00ff00"

    def test_update_label_keeps_own_name(self, db):
        label = db.create_label("Keep", "#ff0000")
        assert isinstance(label, Label)
        error = db.update_label(label.id, "Keep", "#ff0000")
        assert error is None

    def test_update_label_duplicate(self, db):
        db.create_label("A", "#ff0000")
        b = db.create_label("B", "#00ff00")
        assert isinstance(b, Label)
        error = db.update_label(b.id, "A", "#123456")
        assert error == "Label name 'A' already exists"
        error = db.update_label(b.id, "B", "#ff0000")
        assert error == "Label color '#ff0000' already in use"

    def test_create_label_invalid_color(self, db):
        result = db.create_label("Bad", "#zzzzzz")
        assert result == "Invalid color format: '#zzzzzz' (expected #rrggbb)"

    def test_update_label_invalid_color(self, db):
        label = db.create_label("OK", "#ff0000")
        assert isinstance(label, Label)
        error = db.update_label(label.id, "OK", "red")
        assert error == "Invalid color format: 'red' (expected #rrggbb)"

    def test_delete_label_clears_cards(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        label = db.create_label("Tag", "#ff0000")
        assert isinstance(label, Label)
        card = db.create_card(col.id, "A", 0)
        db.update_card_label(card.id, label.id)
        db.delete_label(label.id)
        assert db.get_labels() == []
        assert db.get_cards(col.id)[0].label_id is None


class TestForeignKeyCascade:
    """DB-level ON DELETE CASCADE (raw DELETE bypasses the ORM cascade)."""

    def test_raw_delete_column_cascades_cards(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        db.create_card(col.id, "Card", 0)
        with db.session() as s:
            s.exec(delete(Column).where(Column.id == col.id))
            s.commit()
        assert db.get_cards(col.id) == []

    def test_raw_delete_board_cascades_columns_and_cards(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        db.create_card(col.id, "Card", 0)
        with db.session() as s:
            s.exec(delete(Board).where(Board.id == board.id))
            s.commit()
        assert db.get_columns(board.id) == []
        assert db.get_cards(col.id) == []

    def test_raw_delete_card_keeps_rest(self, db):
        board = _new_board(db)
        col = db.create_column(board.id)
        card = db.create_card(col.id, "Card", 0)
        with db.session() as s:
            s.exec(delete(Card).where(Card.id == card.id))
            s.commit()
        assert db.get_cards(col.id) == []
