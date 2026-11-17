"""World creation and ownership-gated updates."""

from uuid import uuid4

from app.domain import permissions
from app.domain.models import UserId, World, WorldId
from app.domain.repositories import Repositories
from app.services.access import PermissionDeniedError, WorldNotFoundError


async def create_world(
    repos: Repositories, owner_id: UserId, name: str, description: str | None = None, pic: str | None = None
) -> WorldId:
    world = World(id=str(uuid4()), owner_id=owner_id, name=name, description=description, pic=pic)
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
