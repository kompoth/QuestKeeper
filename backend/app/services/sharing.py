"""Orchestrates permission grants and world invites. Granting and inviting are world-owner-only."""

from dataclasses import dataclass

from app.domain import permissions
from app.domain.models import EntityId, EntityPermission, PermissionLevel, UserId, WorldId, WorldInvite
from app.domain.repositories import Repositories
from app.services.access import EntityNotFoundError, PermissionDeniedError, UserNotFoundError, WorldNotFoundError


@dataclass(frozen=True)
class InviteGrant:
    """The access a `create_invite` call will hand the invitee once they accept."""

    entity_id: EntityId
    level: PermissionLevel


async def _require_owner(repos: Repositories, user_id: UserId, world_id: WorldId) -> None:
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)


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


async def create_invite(
    repos: Repositories, user_id: UserId, world_id: WorldId, invitee_email: str, grant: InviteGrant
) -> WorldInvite:
    await _require_owner(repos, user_id, world_id)

    invitee = await repos.users.get_by_email(invitee_email)
    if invitee is None:
        raise UserNotFoundError(invitee_email)

    entity = await repos.entities.get(world_id, grant.entity_id)
    if entity is None:
        raise EntityNotFoundError(grant.entity_id)

    invite = WorldInvite(world_id=world_id, invitee_id=invitee.id, entity_id=grant.entity_id, level=grant.level)
    await repos.invites.create(invite)
    return invite


async def accept_invite(repos: Repositories, user_id: UserId, invite: WorldInvite) -> None:
    """Accepts a pending invite on the invitee's behalf; `invite` must be one of their own pending invites."""
    if invite.invitee_id != user_id:
        raise PermissionDeniedError(user_id, invite.world_id)

    await repos.invites.accept(invite)
