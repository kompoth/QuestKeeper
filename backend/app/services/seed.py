"""Bootstraps the first admin account on startup, from configured credentials.

A no-op once any admin exists - safe to leave the configured credentials in place
indefinitely. Role changes after that point go through the normal admin UI instead.
"""

from uuid import uuid4

from app.domain.models import User, UserRole
from app.domain.repositories import Repositories
from app.domain.security import hash_password


async def ensure_seed_admin(repos: Repositories, email: str, password: str) -> None:
    """Raises EmailAlreadyRegisteredError if another process wins a concurrent seed race - the
    caller owns the session and must roll it back on that, same as every other repo-port error.
    """
    if await repos.users.has_admin():
        return

    existing = await repos.users.get_by_email(email)
    if existing is None:
        user = User(
            id=str(uuid4()), name="Admin", email=email, hashed_password=hash_password(password), role=UserRole.ADMIN
        )
        await repos.users.create(user)
    elif existing.role != UserRole.ADMIN:
        await repos.users.update_role(existing.id, UserRole.ADMIN)
