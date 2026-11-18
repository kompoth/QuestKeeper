"""Email-based password recovery: request a reset link, then consume it."""

import secrets
from datetime import UTC, datetime, timedelta

from app.domain.mail import Mailer
from app.domain.models import PasswordReset, User, UserId, UserStatus
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services.access import PasswordResetTokenNotFoundError, UserNotFoundError

RESET_TOKEN_TTL = timedelta(hours=1)


async def _create_and_send_reset(repos: Repositories, mailer: Mailer, user: User, *, frontend_origin: str) -> None:
    reset = PasswordReset(
        token=secrets.token_urlsafe(32), user_id=user.id, expires_at=datetime.now(UTC) + RESET_TOKEN_TTL
    )
    await repos.password_resets.create(reset)
    reset_url = f"{frontend_origin}/login/reset-password?token={reset.token}"
    await mailer.send_password_reset(to_email=user.email, reset_url=reset_url)


async def request_password_reset(repos: Repositories, mailer: Mailer, email: str, *, frontend_origin: str) -> None:
    """No-ops silently for an unknown email - callers must never reveal account existence."""
    user = await repos.users.get_by_email(email)
    if user is None:
        return
    await _create_and_send_reset(repos, mailer, user, frontend_origin=frontend_origin)


async def request_password_reset_for_user(
    repos: Repositories, mailer: Mailer, user_id: UserId, *, frontend_origin: str
) -> None:
    """Admin-triggered equivalent of request_password_reset, for a known user_id - raises if missing."""
    user = await repos.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    await _create_and_send_reset(repos, mailer, user, frontend_origin=frontend_origin)


async def reset_password(repos: Repositories, token: str, new_password: str) -> None:
    reset = await repos.password_resets.get(token)
    if reset is None:
        raise PasswordResetTokenNotFoundError(token)

    await repos.users.update_password(reset.user_id, hash_password(new_password))

    # An admin-created account is PENDING until its first password is set - that's what activates it.
    user = await repos.users.get_by_id(reset.user_id)
    if user is not None and user.status == UserStatus.PENDING:
        await repos.users.update_status(reset.user_id, UserStatus.ACTIVE)

    await repos.password_resets.delete(token)
    await repos.sessions.delete_all_for_user(reset.user_id)
