"""World creation, listing, and ownership-gated updates."""

import secrets
from collections.abc import Sequence

from app.domain import permissions
from app.domain.models import UserId, World, WorldId
from app.domain.repositories import Repositories
from app.services.access import IdCollisionError, PermissionDeniedError, WorldNotFoundError


async def list_worlds(repos: Repositories, user_id: UserId) -> Sequence[World]:
    """Worlds the user owns or holds any permission grant in."""
    return await repos.worlds.list_for_user(user_id)


async def get_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> World:
    """The world, for a caller who owns it or holds any permission grant in it."""
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)

    if not permissions.is_owner(world, user_id):
        grants = await repos.permissions.get_grants(world_id, user_id)
        if not grants:
            raise PermissionDeniedError(user_id, world_id)

    return world


async def create_world(
    repos: Repositories, owner_id: UserId, name: str, description: str | None = None, pic: str | None = None
) -> WorldId:
    world = World(id=secrets.token_urlsafe(9), owner_id=owner_id, name=name, description=description, pic=pic)
    try:
        await repos.worlds.create(world)
    except IdCollisionError:
        # Vanishingly unlikely - regenerate and retry exactly once rather than fail the request.
        world = world.model_copy(update={"id": secrets.token_urlsafe(9)})
        await repos.worlds.create(world)
    return world.id


async def update_world(repos: Repositories, user_id: UserId, world: World) -> None:
    """Replaces the name/description/pic of the existing world matching `world.id`.

    `world.owner_id` is ignored; ownership never changes through this call.
    """
    existing = await repos.worlds.get(world.id)
    if existing is None:
        raise WorldNotFoundError(world.id)
    if not permissions.is_owner(existing, user_id):
        raise PermissionDeniedError(user_id, world.id)

    updated = existing.model_copy(update={"name": world.name, "description": world.description, "pic": world.pic})
    await repos.worlds.update(updated)


async def delete_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> None:
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)

    await repos.worlds.delete(world_id)
