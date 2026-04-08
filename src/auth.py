"""Simple API-key auth via cookie for single-user access."""

import hashlib
import hmac
import os
from collections.abc import Awaitable, Callable

from nicegui import app, ui
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

COOKIE_NAME = "todo_auth"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
_LOGIN_PATH = "/login"

# Required env var — app won't start without it.
API_KEY: str = os.environ.get("NICEGUI_API_KEY", "")


def _make_token(api_key: str) -> str:
    """Derive a cookie token from the API key (avoid storing the raw key)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _is_valid_token(token: str) -> bool:
    """Check the cookie token against the configured API key."""
    return hmac.compare_digest(token, _make_token(API_KEY))


def _is_public(path: str) -> bool:
    """Paths that must be accessible without auth."""
    return path == _LOGIN_PATH or path.startswith("/_nicegui/")


def setup_auth() -> None:
    """Register middleware and login page. Raises if NICEGUI_API_KEY is unset."""
    if not API_KEY:
        msg = "Environment variable NICEGUI_API_KEY must be set."
        raise RuntimeError(msg)

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

        # Redirect browsers to login; reject API/WS with 403.
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(_LOGIN_PATH, status_code=303)
        return Response("Forbidden", status_code=403)

    @ui.page(_LOGIN_PATH)
    def login_page() -> None:
        """Minimal login form — enter the API key once per device."""

        def _submit() -> None:
            if not hmac.compare_digest(
                hashlib.sha256(inp.value.encode()).hexdigest(),
                _make_token(API_KEY),
            ):
                ui.notify("Wrong key", type="negative")
                return
            # Set the auth cookie via JavaScript, then redirect.
            token = _make_token(API_KEY)
            ui.run_javascript(
                f'document.cookie="{COOKIE_NAME}={token};path=/;max-age={COOKIE_MAX_AGE};SameSite=Strict";'
                'window.location="/"'
            )

        with ui.card().classes("absolute-center q-pa-lg"):
            ui.label("Enter access key").classes("text-h6")
            inp = ui.input("Key", password=True, password_toggle_button=True).on(
                "keydown.enter", _submit
            )
            ui.button("Unlock", on_click=_submit)
