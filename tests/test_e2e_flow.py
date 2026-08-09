"""E2E flow test: login → open board → cards → sort → export."""

import asyncio
from types import SimpleNamespace

from src import auth
from src.database import Database
from src.models import Board, Label
from src.services.export_service import export as _export


class _FakeApp:
    """Pass-through decorators that record the registered handlers."""

    def __init__(self) -> None:
        self.handlers: dict[tuple, object] = {}

    def middleware(self, kind: str):
        def decorator(fn):
            self.handlers[("middleware", kind)] = fn
            return fn

        return decorator

    def post(self, path: str):
        def decorator(fn):
            self.handlers[("post", path)] = fn
            return fn

        return decorator


def _fake_request(*, cookies: dict | None = None, accept: str = "") -> SimpleNamespace:
    headers = {"accept": accept} if accept else {}
    return SimpleNamespace(
        url=SimpleNamespace(path="/", scheme="http"),
        cookies=cookies or {},
        headers=headers,
    )


def _run(coro):
    return asyncio.run(coro)


async def _pass_through(_request):
    return "ok"


def test_login_board_cards_sort_export(db: Database, monkeypatch) -> None:
    """Full user journey: login, create board, add cards, sort, export."""
    monkeypatch.setattr(auth, "API_KEY", "s3cret")
    monkeypatch.setattr(auth, "_SUBPATH", "")
    fake = _FakeApp()
    monkeypatch.setattr(auth, "app", fake)
    auth._register_login_post("/login", "/")
    auth._register_middleware("/login")

    login = _run(fake.handlers[("post", "/login/submit")](_fake_request(), "s3cret"))
    assert login.status_code == 303
    token = login.headers["set-cookie"].split(";")[0].split("=", 1)[1]
    authorized = _run(
        fake.handlers[("middleware", "http")](
            _fake_request(cookies={auth.COOKIE_NAME: token}),
            _pass_through,
        )
    )
    assert authorized == "ok"

    board = db.add_board("planning", "Planning")
    assert isinstance(board, Board)
    assert db.get_board_by_key("planning") is not None

    col = db.create_column(board.id)
    label_work = db.create_label("Work", "#ff0000")
    label_home = db.create_label("Home", "#00ff00")
    assert isinstance(label_work, Label)
    assert isinstance(label_home, Label)

    db.create_card(col.id, "Buy milk", 0)
    report = db.create_card(col.id, "Write report", 1)
    bank = db.create_card(col.id, "Call bank", 2)
    archive = db.create_card(col.id, "Archive old files", 3)

    db.update_card_prio(report.id, prio=True)
    db.update_card_label(report.id, label_work.id)
    db.update_card_label(bank.id, label_home.id)
    db.update_card_completed(archive.id, is_completed=True)

    board = db.get_board_by_key("planning")
    assert board is not None
    db.sort_cards_by_prio_label_name(board, db.get_labels())

    fresh = db.get_board_by_key("planning")
    assert fresh is not None
    assert [c.title for c in fresh.columns[0].cards] == [
        "Write report",
        "Buy milk",
        "Call bank",
        "Archive old files",
    ]

    labels = db.get_labels()
    assert _export(fresh, labels) == (
        "## Planning\n\n### New Column\n"
        "- [ ] Write report (Work) ⚑\n"
        "- [ ] Buy milk\n"
        "- [ ] Call bank (Home)\n"
        "- [x] Archive old files\n"
    )
    assert _export(fresh, labels, completed_only=True) == (
        "## Planning\n\n### New Column\n- Archive old files\n"
    )
