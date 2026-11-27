"""Admin-facing user listing, creation, and role management."""

import secrets
from collections.abc import Sequence
from uuid import uuid4

from app.domain.mail import Mailer
from app.domain.models import User, UserId, UserRole, UserStatus
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services.errors import (
    CannotBanSelfError,
    CannotChangeOwnRoleError,
    InvalidStatusTransitionError,
    UserNotFoundError,
)
from app.services.password_reset import request_password_reset_for_user


async def list_users(
    repos: Repositories, offset: int, limit: int, search: str | None = None
) -> tuple[Sequence[User], int]:
    users = await repos.users.list_page(offset, limit, search)
    total = await repos.users.count(search)
    return users, total


async def create_user(  # noqa: PLR0913 -- repos/mailer/frontend_origin are distinct capability params
    repos: Repositories, mailer: Mailer, name: str, email: str, role: UserRole, *, frontend_origin: str
) -> User:
    """Creates an admin-added account PENDING a password, then emails a set-password link.

    Completing the password reset activates the account (see password_reset.reset_password).
    Raises EmailAlreadyRegisteredError if the email is taken.
    """
    user = User(
        id=str(uuid4()),
        name=name,
        email=email,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        role=role,
        status=UserStatus.PENDING,
    )
    await repos.users.create(user)
    await request_password_reset_for_user(repos, mailer, user.id, frontend_origin=frontend_origin)
    return user


async def change_user_role(repos: Repositories, actor_id: UserId, user_id: UserId, role: UserRole) -> User:
    """Raises CannotChangeOwnRoleError if the acting admin targets their own account."""
    if actor_id == user_id:
        raise CannotChangeOwnRoleError(user_id)

    user = await repos.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)

    await repos.users.update_role(user_id, role)
    return user.model_copy(update={"role": role})


async def change_user_status(repos: Repositories, actor_id: UserId, user_id: UserId, status: UserStatus) -> User:
    """Raises CannotBanSelfError if the acting admin targets their own account with BANNED.

    Raises InvalidStatusTransitionError if either the target status or the user's current status is
    PENDING - that's a system-managed state until the person completes signup, not an admin toggle.
    """
    if status == UserStatus.PENDING:
        raise InvalidStatusTransitionError(user_id)
    if status == UserStatus.BANNED and actor_id == user_id:
        raise CannotBanSelfError(user_id)

    user = await repos.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    if user.status == UserStatus.PENDING:
        raise InvalidStatusTransitionError(user_id)

    await repos.users.update_status(user_id, status)
    return user.model_copy(update={"status": status})
