"""Account creation triggered by accepting an email-only world invite (confirm-by-token flow)."""

from dataclasses import dataclass

from app.domain.models import Session, User, UserStatus
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

    user = await repos.users.get_by_id(invite.invitee_id)
    if user is None:
        raise InviteTokenNotFoundError(token)
    if user.status != UserStatus.PENDING:
        raise EmailAlreadyRegisteredError(user.email)

    await repos.users.claim(user.id, name, hash_password(password))
    await accept_invite(repos, user.id, invite)

    session = await auth.login(repos, user.email, password)
    claimed = user.model_copy(update={"name": name, "status": UserStatus.ACTIVE})
    return SignupResult(user=claimed, session=session)
