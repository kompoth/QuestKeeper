"""Session/CSRF cookie helpers shared by routes that establish or replace a login session."""

import secrets

from fastapi import Response

from app.api.dependencies import CSRF_COOKIE_NAME
from app.config import get_cookie_secure
from app.services import auth


def set_session_cookies(response: Response, token: str) -> None:
    max_age = int(auth.SESSION_TTL.total_seconds())
    secure = get_cookie_secure()
    response.set_cookie(auth.SESSION_COOKIE_NAME, token, max_age=max_age, httponly=True, secure=secure, samesite="lax")
    response.set_cookie(
        CSRF_COOKIE_NAME, secrets.token_urlsafe(32), max_age=max_age, httponly=False, secure=secure, samesite="lax"
    )
