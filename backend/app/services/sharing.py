"""Orchestrates permission grants and world invites. Granting and inviting are world-owner-only."""

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain import permissions
from app.domain.mail import Mailer
from app.domain.models import (
    EntityId,
    EntityPermission,
    PermissionLevel,
    User,
    UserId,
    UserRole,
    UserStatus,
    World,
    WorldId,
    WorldInvite,
)
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services.access import EntityNotFoundError, InviteNotFoundError, PermissionDeniedError, WorldNotFoundError

INVITE_TOKEN_TTL = timedelta(days=7)


@dataclass(frozen=True)
class InviteGrant:
    """The access a `create_invite` call will hand the invitee once they accept."""

    entity_id: EntityId
    level: PermissionLevel


async def _require_owner(repos: Repositories, user_id: UserId, world_id: WorldId) -> World:
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)
    return world


async def grant_permission(repos: Repositories, user_id: UserId, world_id: WorldId, grant: EntityPermission) -> None:
    await _require_owner(repos, user_id, world_id)

    entity = await repos.entities.get(world_id, grant.entity_id)
    if entity is None:
        raise EntityNotFoundError(grant.entity_id)

    await repos.permissions.grant(grant.user_id, grant.entity_id, grant.level)


async def revoke_permission(
    repos: Repositories, user_id: UserId, world_id: WorldId, grantee_id: UserId, entity_id: EntityId
) -> None:
    await _require_owner(repos, user_id, world_id)
    await repos.permissions.revoke(grantee_id, entity_id)


async def create_invite(  # noqa: PLR0913, PLR0917 -- repos/mailer/frontend_origin are distinct capability params
    repos: Repositories,
    mailer: Mailer,
    user_id: UserId,
    world_id: WorldId,
    invitee_email: str,
    grant: InviteGrant,
    *,
    frontend_origin: str,
) -> WorldInvite:
    world = await _require_owner(repos, user_id, world_id)

    entity = await repos.entities.get(world_id, grant.entity_id)
    if entity is None:
        raise EntityNotFoundError(grant.entity_id)

    invitee = await repos.users.get_by_email(invitee_email)

    if invitee is not None and invitee.status != UserStatus.PENDING:
        invite = WorldInvite(
            id=str(uuid4()), world_id=world_id, invitee_id=invitee.id, entity_id=grant.entity_id, level=grant.level
        )
        invite = await repos.invites.create(invite)
        await mailer.send_existing_user_invite(to_email=invitee_email, world_name=world.name)
        return invite

    if invitee is None:
        placeholder = User(
            id=str(uuid4()),
            name=invitee_email,
            email=invitee_email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.MEMBER,
            status=UserStatus.PENDING,
        )
        await repos.users.create(placeholder)
        invitee_id = placeholder.id
    else:
        invitee_id = invitee.id

    token = secrets.token_urlsafe(32)
    invite = WorldInvite(
        id=str(uuid4()),
        world_id=world_id,
        invitee_id=invitee_id,
        entity_id=grant.entity_id,
        level=grant.level,
        confirmation_token=token,
        token_expires_at=datetime.now(UTC) + INVITE_TOKEN_TTL,
    )
    invite = await repos.invites.create(invite)
    confirm_url = f"{frontend_origin}/invites/confirm?token={token}"
    await mailer.send_new_user_invite(to_email=invitee_email, world_name=world.name, confirm_url=confirm_url)
    return invite


async def list_invites_for_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> Sequence[WorldInvite]:
    await _require_owner(repos, user_id, world_id)
    return await repos.invites.get_all_for_world(world_id)


async def accept_invite(repos: Repositories, user_id: UserId, invite: WorldInvite) -> None:
    """Accepts a pending invite on the invitee's behalf; `invite` must be one of their own pending invites."""
    if invite.invitee_id != user_id:
        raise PermissionDeniedError(user_id, invite.world_id)

    await repos.invites.accept(invite)


async def list_pending_invites(repos: Repositories, user_id: UserId) -> Sequence[WorldInvite]:
    return await repos.invites.get_pending_for_user(user_id)


async def accept_invite_for_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> None:
    """Accepts the caller's pending invite for `world_id`, found among their own pending invites."""
    pending = await repos.invites.get_pending_for_user(user_id)
    invite = next((candidate for candidate in pending if candidate.world_id == world_id), None)
    if invite is None:
        raise InviteNotFoundError(user_id, world_id)

    await accept_invite(repos, user_id, invite)
