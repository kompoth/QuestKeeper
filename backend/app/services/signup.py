"""Account creation triggered by accepting an email-only world invite (confirm-by-token flow)."""

from dataclasses import dataclass
from uuid import uuid4

from app.domain.models import Session, User, UserRole
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services import auth
from app.services.access import EmailAlreadyRegisteredError, InviteTokenNotFoundError
from app.services.sharing import accept_invite


@dataclass(frozen=True)
class SignupResult:
    user: User
    session: Session


async def confirm_invite_signup(repos: Repositories, token: str, name: str, password: str) -> SignupResult:
    invite = await repos.invites.get_by_token(token)
    if invite is None:
        raise InviteTokenNotFoundError(token)

    existing = await repos.users.get_by_email(invite.invitee_email)
    if existing is not None:
        raise EmailAlreadyRegisteredError(invite.invitee_email)

    user = User(
        id=str(uuid4()),
        name=name,
        email=invite.invitee_email,
        hashed_password=hash_password(password),
        role=UserRole.MEMBER,
    )
    await repos.users.create(user)

    # Generalized backfill: every pending invite for this email, not just the one tied to this token.
    await repos.invites.link_pending_to_user(invite.invitee_email, user.id)

    await accept_invite(repos, user.id, invite.model_copy(update={"invitee_id": user.id}))

    session = await auth.login(repos, invite.invitee_email, password)
    return SignupResult(user=user, session=session)
