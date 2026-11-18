"""Permission grants and world invites."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, Response, status

from app.api.cookies import set_session_cookies
from app.api.dependencies import CurrentUser, MailerDep, Repos, SettingsDep, require_csrf
from app.api.schemas import ConfirmInviteRequest, CreateInviteRequest, InviteSummary, PendingInviteOut, UserOut
from app.domain.models import EntityId, EntityPermission, User, UserId, WorldId
from app.services.sharing import (
    InviteGrant,
    accept_invite_for_world,
    create_invite,
    grant_permission,
    list_invites_for_world,
    list_pending_invites,
    revoke_permission,
)
from app.services.signup import confirm_invite_signup

permissions_router = APIRouter(prefix="/worlds/{world_id}", tags=["sharing"])
invites_router = APIRouter(prefix="/invites", tags=["sharing"])


@permissions_router.post("/permissions", dependencies=[Depends(require_csrf)])
async def grant(world_id: WorldId, body: EntityPermission, user: CurrentUser, repos: Repos) -> None:
    await grant_permission(repos, user.id, world_id, body)


@permissions_router.delete(
    "/permissions/{grantee_id}/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def revoke(world_id: WorldId, grantee_id: UserId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> None:
    await revoke_permission(repos, user.id, world_id, grantee_id, entity_id)


@permissions_router.post("/invites", dependencies=[Depends(require_csrf)])
async def invite(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    body: CreateInviteRequest,
    user: CurrentUser,
    repos: Repos,
    mailer: MailerDep,
    settings: SettingsDep,
) -> InviteSummary:
    grant_ = InviteGrant(entity_id=body.entity_id, level=body.level)
    invite_ = await create_invite(
        repos, mailer, user.id, world_id, body.invitee_email, grant_, frontend_origin=settings.frontend_origin
    )
    # The invite's invitee always resolves to body.invitee_email - no need to re-fetch the user.
    return InviteSummary.from_invite(invite_, body.invitee_email)


@permissions_router.get("/invites")
async def list_invites(world_id: WorldId, user: CurrentUser, repos: Repos) -> Sequence[InviteSummary]:
    invites = await list_invites_for_world(repos, user.id, world_id)
    summaries = []
    for invite_ in invites:
        invitee = await repos.users.get_by_id(invite_.invitee_id)
        summaries.append(InviteSummary.from_invite(invite_, invitee.email if invitee else ""))
    return summaries


@invites_router.get("")
async def list_my_invites(user: CurrentUser, repos: Repos) -> Sequence[PendingInviteOut]:
    invites = await list_pending_invites(repos, user.id)
    return [PendingInviteOut.from_invite(invite_) for invite_ in invites]


@invites_router.post("/{world_id}/accept", dependencies=[Depends(require_csrf)])
async def accept(world_id: WorldId, user: CurrentUser, repos: Repos) -> None:
    await accept_invite_for_world(repos, user.id, world_id)


@invites_router.post("/confirm", response_model=UserOut)
async def confirm(body: ConfirmInviteRequest, response: Response, repos: Repos) -> User:
    result = await confirm_invite_signup(repos, body.token, body.name, body.password)
    set_session_cookies(response, result.session.token)
    return result.user
