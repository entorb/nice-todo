"""Simple API-key auth via cookie for single-user access."""

import hashlib
import hmac
import os
from collections.abc import Awaitable, Callable

from fastapi import Form
from nicegui import app, ui
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

COOKIE_NAME = "todo_auth"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
_LOGIN_ROUTE = "/login"
_LOGIN_POST_ROUTE = "/login/submit"
_LOGOUT_ROUTE = "/logout"

# Required env var — app won't start without it.
API_KEY: str = os.environ.get("NICEGUI_API_KEY", "")
_SUBPATH: str = os.environ.get("NICEGUI_SUBPATH", "")


def _make_token(api_key: str) -> str:
    """Derive a cookie token from the API key (avoid storing the raw key)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _is_valid_token(token: str) -> bool:
    """Check the cookie token against the configured API key."""
    return hmac.compare_digest(token, _make_token(API_KEY))


def _is_public(path: str) -> bool:
    """Paths that must be accessible without auth."""
    login_prefix = f"{_SUBPATH}{_LOGIN_ROUTE}"
    logout_prefix = f"{_SUBPATH}{_LOGOUT_ROUTE}"
    nicegui_prefix = f"{_SUBPATH}/_nicegui/"
    socketio_prefix = f"{_SUBPATH}/socket.io/"
    public_prefixes = (
        login_prefix,
        logout_prefix,
        nicegui_prefix,
        socketio_prefix,
        "/_nicegui/",
        "/socket.io/",
    )
    return any(path.startswith(p) for p in public_prefixes)


def _register_middleware(login_url: str) -> None:
    """Register the auth-check middleware."""

    @app.middleware("http")
    async def _auth_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Block unauthenticated requests."""
        if _is_public(request.url.path):
            return await call_next(request)

        token = request.cookies.get(COOKIE_NAME)
        if token and _is_valid_token(token):
            return await call_next(request)

        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(login_url, status_code=303)
        return Response("Forbidden", status_code=403)


def _register_login_post(login_url: str, home_url: str) -> None:
    """Register the POST endpoint that sets the auth cookie server-side."""

    @app.post(_LOGIN_POST_ROUTE)
    async def _login_submit(key: str = Form()) -> Response:
        """Validate the key and set an auth cookie."""
        if not hmac.compare_digest(key, API_KEY):
            return RedirectResponse(f"{login_url}?error=1", status_code=303)
        response = RedirectResponse(home_url, status_code=303)
        response.set_cookie(
            COOKIE_NAME,
            _make_token(API_KEY),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/",
        )
        return response


def _register_logout(login_url: str) -> None:
    """Register the logout endpoint that deletes the auth cookie."""

    @app.get(_LOGOUT_ROUTE)
    async def _logout() -> Response:
        """Delete the auth cookie and redirect to login."""
        response = RedirectResponse(login_url, status_code=303)
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
        )
        return response


def _register_login_page() -> None:
    """Register the NiceGUI login page."""

    @ui.page(_LOGIN_ROUTE)
    def login_page(error: str = "") -> None:
        """Minimal login form — enter the API key once per device."""
        with ui.card().classes("absolute-center q-pa-lg"):
            ui.label("Enter access key").classes("text-h6")
            if error:
                ui.label("Wrong key").classes("text-negative")
            with ui.element("form").props(
                f'action="{_SUBPATH}{_LOGIN_POST_ROUTE}" method="post"'
            ):
                ui.input("Key", password=True, password_toggle_button=True).props(
                    'name="key"'
                )
                ui.button("Unlock").props('type="submit"')


def setup_auth() -> None:
    """Register middleware and login page. Raises if NICEGUI_API_KEY is unset."""
    if not API_KEY:
        msg = "Environment variable NICEGUI_API_KEY must be set."
        raise RuntimeError(msg)

    login_url = f"{_SUBPATH}{_LOGIN_ROUTE}"
    home_url = f"{_SUBPATH}/"

    _register_middleware(login_url)
    _register_login_post(login_url, home_url)
    _register_logout(login_url)
    _register_login_page()
