"""Open self-registration: request an account, confirm via emailed token to create it."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.mail import Mailer
from app.domain.models import PendingRegistration, User, UserRole
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services import auth
from app.services.access import EmailAlreadyRegisteredError, RegistrationTokenNotFoundError
from app.services.signup import SignupResult

REGISTRATION_TOKEN_TTL = timedelta(hours=24)


async def request_registration(  # noqa: PLR0913 -- repos/mailer/frontend_origin are distinct capability params
    repos: Repositories, mailer: Mailer, name: str, email: str, password: str, *, frontend_origin: str
) -> None:
    if await repos.users.get_by_email(email) is not None:
        raise EmailAlreadyRegisteredError(email)

    pending = PendingRegistration(
        token=secrets.token_urlsafe(32),
        name=name,
        email=email,
        hashed_password=hash_password(password),
        expires_at=datetime.now(UTC) + REGISTRATION_TOKEN_TTL,
    )
    pending = await repos.pending_registrations.create(pending)
    confirm_url = f"{frontend_origin}/register/confirm?token={pending.token}"
    await mailer.send_registration_confirmation(to_email=email, confirm_url=confirm_url)


async def confirm_registration(repos: Repositories, token: str) -> SignupResult:
    pending = await repos.pending_registrations.get_by_token(token)
    if pending is None:
        raise RegistrationTokenNotFoundError(token)

    if await repos.users.get_by_email(pending.email) is not None:
        raise EmailAlreadyRegisteredError(pending.email)

    user = User(
        id=str(uuid4()),
        name=pending.name,
        email=pending.email,
        hashed_password=pending.hashed_password,
        role=UserRole.MEMBER,
    )
    await repos.users.create(user)
    await repos.pending_registrations.delete(token)

    # Same generalized backfill as confirm_invite_signup: pick up any invites sent to this email
    # before the person ever self-registered.
    await repos.invites.link_pending_to_user(pending.email, user.id)

    session = await auth.create_session(repos, user.id)
    return SignupResult(user=user, session=session)
