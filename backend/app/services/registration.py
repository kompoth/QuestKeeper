"""Open self-registration: request an account, confirm via emailed token to activate it."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.mail import Mailer
from app.domain.models import RegistrationConfirmation, User, UserRole, UserStatus
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services import auth
from app.services.errors import EmailAlreadyRegisteredError, RegistrationTokenNotFoundError
from app.services.signup import SignupResult

REGISTRATION_TOKEN_TTL = timedelta(hours=24)


async def request_registration(  # noqa: PLR0913 -- repos/mailer/frontend_origin are distinct capability params
    repos: Repositories, mailer: Mailer, name: str, email: str, password: str, *, frontend_origin: str
) -> None:
    """Creates (or refreshes, if one is already pending) a PENDING user row reserving `email`."""
    existing = await repos.users.get_by_email(email)
    if existing is not None and existing.status != UserStatus.PENDING:
        raise EmailAlreadyRegisteredError(email)

    hashed_password = hash_password(password)
    if existing is None:
        user = User(
            id=str(uuid4()),
            name=name,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.MEMBER,
            status=UserStatus.PENDING,
        )
        await repos.users.create(user)
        user_id = user.id
    else:
        await repos.users.update_registration_pending(existing.id, name, hashed_password)
        user_id = existing.id

    confirmation = RegistrationConfirmation(
        token=secrets.token_urlsafe(32), user_id=user_id, expires_at=datetime.now(UTC) + REGISTRATION_TOKEN_TTL
    )
    await repos.registration_confirmations.create(confirmation)

    confirm_url = f"{frontend_origin}/register/confirm?token={confirmation.token}"
    await mailer.send_registration_confirmation(to_email=email, confirm_url=confirm_url)


async def confirm_registration(repos: Repositories, token: str) -> SignupResult:
    confirmation = await repos.registration_confirmations.get(token)
    if confirmation is None:
        raise RegistrationTokenNotFoundError(token)

    user = await repos.users.get_by_id(confirmation.user_id)
    if user is None or user.status != UserStatus.PENDING:
        raise RegistrationTokenNotFoundError(token)

    await repos.users.update_status(user.id, UserStatus.ACTIVE)
    await repos.registration_confirmations.delete(token)
    activated = user.model_copy(update={"status": UserStatus.ACTIVE})

    session = await auth.create_session(repos, activated.id)
    return SignupResult(user=activated, session=session)
