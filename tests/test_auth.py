import asyncio
import hashlib
from types import SimpleNamespace

import pytest

from src import auth


class FakeApp:
    """Pass-through decorators that record the registered handlers."""

    def __init__(self):
        self.handlers = {}

    def _decorator(self, key):
        def decorator(fn):
            self.handlers[key] = fn
            return fn

        return decorator

    def middleware(self, kind):
        return self._decorator(("middleware", kind))

    def post(self, path):
        return self._decorator(("post", path))

    def get(self, path):
        return self._decorator(("get", path))


class FakeUI:
    """Page recorder — setup_auth registers the login page on ui.page."""

    def __init__(self):
        self.pages = {}

    def page(self, path):
        def decorator(fn):
            self.pages[path] = fn
            return fn

        return decorator


@pytest.fixture
def auth_env(monkeypatch) -> FakeApp:
    """App stub + a configured API key, ready for handler registration."""
    fake = FakeApp()
    monkeypatch.setattr(auth, "app", fake)
    monkeypatch.setattr(auth, "API_KEY", "secret")
    monkeypatch.setattr(auth, "_SUBPATH", "")
    return fake


def _fake_request(
    path: str = "/",
    *,
    cookies: dict | None = None,
    accept: str = "",
    scheme: str = "http",
) -> SimpleNamespace:
    headers = {"accept": accept} if accept else {}
    return SimpleNamespace(
        url=SimpleNamespace(path=path, scheme=scheme),
        cookies=cookies or {},
        headers=headers,
    )


def _run(coro):
    return asyncio.run(coro)


async def _pass_through(_request):
    return "ok"


def test_make_token_is_sha256_hexdigest():
    assert auth._make_token("secret") == hashlib.sha256(b"secret").hexdigest()


def test_is_valid_token(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret")
    assert auth._is_valid_token(auth._make_token("secret"))
    assert not auth._is_valid_token("wrong")
    assert not auth._is_valid_token("")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/login", True),
        ("/login/submit", True),
        ("/login/foo", True),
        ("/logout", True),
        ("/_nicegui", True),
        ("/_nicegui/x", True),
        ("/socket.io", True),
        ("/apple-touch-icon.png", True),
        ("/", False),
        ("/?key=abc", False),
        ("/board", False),
        ("/loginx", False),
    ],
)
def test_is_public_no_subpath(monkeypatch, path, expected):
    monkeypatch.setattr(auth, "_SUBPATH", "")
    assert auth._is_public(path) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/nice-todo/login", True),
        ("/nice-todo/login/submit", True),
        ("/nice-todo/_nicegui", True),
        ("/nice-todo/socket.io", True),
        ("/nice-todo/", False),
        ("/nice-todo/board", False),
        ("/login", False),
    ],
)
def test_is_public_with_subpath(monkeypatch, path, expected):
    monkeypatch.setattr(auth, "_SUBPATH", "/nice-todo")
    assert auth._is_public(path) == expected


def test_setup_auth_raises_without_key(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "")
    with pytest.raises(RuntimeError, match="NICEGUI_API_KEY"):
        auth.setup_auth()


class TestMiddleware:
    def test_public_path_passes_through(self, auth_env):
        auth._register_middleware("/login")
        mw = auth_env.handlers[("middleware", "http")]
        calls = []

        async def call_next(request):
            calls.append(request)
            return "ok"

        assert _run(mw(_fake_request(path="/login"), call_next)) == "ok"
        assert len(calls) == 1

    def test_valid_token_passes_through(self, auth_env):
        auth._register_middleware("/login")
        mw = auth_env.handlers[("middleware", "http")]
        token = auth._make_token("secret")
        result = _run(
            mw(_fake_request(cookies={auth.COOKIE_NAME: token}), _pass_through)
        )
        assert result == "ok"

    @pytest.mark.parametrize(
        ("accept", "expected"),
        [
            ("text/html", (303, "/login")),
            ("application/json", (403, None)),
        ],
    )
    def test_missing_token_denied(self, auth_env, accept, expected):
        auth._register_middleware("/login")
        mw = auth_env.handlers[("middleware", "http")]
        resp = _run(mw(_fake_request(accept=accept), _pass_through))
        code, location = expected
        assert resp.status_code == code
        if location:
            assert resp.headers["location"] == location


class TestLoginSubmit:
    def test_wrong_key_redirects_with_error(self, auth_env):
        auth._register_login_post("/login", "/")
        handler = auth_env.handlers[("post", "/login/submit")]

        resp = _run(handler(_fake_request(), "wrong"))
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login?error=1"
        assert "set-cookie" not in resp.headers

    @pytest.mark.parametrize(
        ("scheme", "expect_secure"),
        [("http", False), ("https", True)],
    )
    def test_valid_key_sets_cookie(self, auth_env, scheme, expect_secure):
        auth._register_login_post("/login", "/")
        handler = auth_env.handlers[("post", "/login/submit")]

        resp = _run(handler(_fake_request(scheme=scheme), "secret"))
        cookie = resp.headers["set-cookie"]
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"
        assert f"{auth.COOKIE_NAME}=" in cookie
        assert "httponly" in cookie.lower()
        assert "samesite=strict" in cookie.lower()
        assert "path=/" in cookie.lower()
        assert ("secure" in cookie.lower()) is expect_secure

    def test_subpath_scopes_cookie(self, monkeypatch, auth_env):
        monkeypatch.setattr(auth, "_SUBPATH", "/nice-todo")
        auth._register_login_post("/nice-todo/login", "/nice-todo/")
        handler = auth_env.handlers[("post", "/login/submit")]

        resp = _run(handler(_fake_request(), "secret"))
        assert resp.headers["location"] == "/nice-todo/"
        assert "path=/nice-todo/" in resp.headers["set-cookie"].lower()


class TestLogout:
    def test_deletes_cookie(self, auth_env):
        auth._register_logout("/login")
        handler = auth_env.handlers[("get", "/logout")]

        resp = _run(handler())
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
        assert "todo_auth=" in resp.headers["set-cookie"]

    def test_subpath_scopes_cookie(self, monkeypatch, auth_env):
        monkeypatch.setattr(auth, "_SUBPATH", "/nice-todo")
        auth._register_logout("/login")
        handler = auth_env.handlers[("get", "/logout")]

        resp = _run(handler())
        assert "path=/nice-todo/" in resp.headers["set-cookie"].lower()


class TestSetupAuth:
    def test_registers_all_handlers(self, monkeypatch, auth_env):
        fake_ui = FakeUI()
        monkeypatch.setattr(auth, "ui", fake_ui)
        auth.setup_auth()

        assert ("middleware", "http") in auth_env.handlers
        assert ("post", "/login/submit") in auth_env.handlers
        assert ("get", "/logout") in auth_env.handlers
        assert "/login" in fake_ui.pages
