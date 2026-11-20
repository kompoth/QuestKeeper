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
from app.services.access import (
    EntityNotFoundError,
    InviteNotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
    WorldNotFoundError,
)

INVITE_TOKEN_TTL = timedelta(days=7)


@dataclass(frozen=True)
class EntityGrant:
    user: User
    level: PermissionLevel
    invite_accepted: bool | None
    """None if the grantee has no invite record for this world at all - never invited, just granted directly."""


@dataclass(frozen=True)
class InheritedEntityGrant:
    user: User
    level: PermissionLevel
    invite_accepted: bool | None
    from_entity_id: EntityId


@dataclass(frozen=True)
class EntityPermissionsView:
    direct: Sequence[EntityGrant]
    inherited: Sequence[InheritedEntityGrant]


async def _require_owner(repos: Repositories, user_id: UserId, world_id: WorldId) -> World:
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)
    return world


async def grant_permission(  # noqa: PLR0913, PLR0917 -- repos/world_id/entity_id/grantee_email/level distinct params
    repos: Repositories,
    user_id: UserId,
    world_id: WorldId,
    entity_id: EntityId,
    grantee_email: str,
    level: PermissionLevel,
) -> None:
    await _require_owner(repos, user_id, world_id)

    entity = await repos.entities.get(world_id, entity_id)
    if entity is None:
        raise EntityNotFoundError(entity_id)

    grantee = await repos.users.get_by_email(grantee_email)
    if grantee is None:
        raise UserNotFoundError(grantee_email)

    # Entity access is only ever granted to someone already invited to the world - an invite is
    # what unlocks the world itself; this just narrows what they can see or edit inside it.
    if await repos.invites.get_for_user(world_id, grantee.id) is None:
        raise InviteNotFoundError(world_id, grantee.id)

    await repos.permissions.grant(grantee.id, entity_id, level)


async def revoke_permission(
    repos: Repositories, user_id: UserId, world_id: WorldId, grantee_id: UserId, entity_id: EntityId
) -> None:
    await _require_owner(repos, user_id, world_id)
    await repos.permissions.revoke(grantee_id, entity_id)


async def get_entity_permissions(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId
) -> EntityPermissionsView:
    """Direct grants on this entity, plus grants inherited from ancestors (closest wins per user). Owner-only."""
    await _require_owner(repos, user_id, world_id)

    entity = await repos.entities.get(world_id, entity_id)
    if entity is None:
        raise EntityNotFoundError(entity_id)

    accepted_by_user_id = {
        invite.invitee_id: invite.accepted for invite in await repos.invites.get_all_for_world(world_id)
    }

    async def to_grants(permission_grants: Sequence[EntityPermission]) -> list[EntityGrant]:
        grants = []
        for permission_grant in permission_grants:
            grantee = await repos.users.get_by_id(permission_grant.user_id)
            if grantee is not None:
                grants.append(
                    EntityGrant(
                        user=grantee,
                        level=permission_grant.level,
                        invite_accepted=accepted_by_user_id.get(grantee.id),
                    )
                )
        return grants

    direct = await to_grants(await repos.permissions.get_grants_for_entity(entity_id))
    seen_user_ids = {grant.user.id for grant in direct}

    inherited: list[InheritedEntityGrant] = []
    for ancestor_id in await repos.entities.get_ancestor_ids(world_id, entity_id):
        for grant in await to_grants(await repos.permissions.get_grants_for_entity(ancestor_id)):
            if grant.user.id in seen_user_ids:
                continue
            seen_user_ids.add(grant.user.id)
            inherited.append(
                InheritedEntityGrant(
                    user=grant.user,
                    level=grant.level,
                    invite_accepted=grant.invite_accepted,
                    from_entity_id=ancestor_id,
                )
            )

    return EntityPermissionsView(direct=direct, inherited=inherited)


async def create_invite(  # noqa: PLR0913 -- repos/mailer/frontend_origin are distinct capability params, not data fields
    repos: Repositories, mailer: Mailer, user_id: UserId, world_id: WorldId, invitee_email: str, *, frontend_origin: str
) -> WorldInvite:
    world = await _require_owner(repos, user_id, world_id)

    invitee = await repos.users.get_by_email(invitee_email)

    if invitee is not None and invitee.status != UserStatus.PENDING:
        # No confirmation link is needed - an existing account can already see and accept the
        # invite at /invites once logged in, so no email is sent for this path.
        invite = WorldInvite(id=str(uuid4()), world_id=world_id, invitee_id=invitee.id)
        return await repos.invites.create(invite)

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


async def expel_invitee(repos: Repositories, user_id: UserId, world_id: WorldId, invitee_email: str) -> None:
    """Deletes an invitee's invite record for this world. Owner-only.

    Resolves invitee_email to a user internally - the caller never needs (or sees) invitee_id.
    """
    await _require_owner(repos, user_id, world_id)

    invitee = await repos.users.get_by_email(invitee_email)
    if invitee is None:
        raise InviteNotFoundError(world_id, invitee_email)

    invites = await repos.invites.get_all_for_world(world_id)
    invite = next((candidate for candidate in invites if candidate.invitee_id == invitee.id), None)
    if invite is None:
        raise InviteNotFoundError(world_id, invitee.id)

    await repos.invites.delete(world_id, invitee.id)


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
