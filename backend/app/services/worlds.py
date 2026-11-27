"""World creation, listing, and ownership-gated updates."""

import secrets
from collections.abc import Sequence

from app.domain import permissions
from app.domain.media import MediaStorage, UploadPolicy
from app.domain.models import UserId, World, WorldId
from app.domain.repositories import Repositories
from app.services.errors import IdCollisionError, PermissionDeniedError, WorldNotFoundError, WorldNotInTrashError
from app.services.media import (
    entity_media_prefix,
    extract_world_pic_file_id,
    mint_upload,
    world_pic_key,
    world_pic_prefix,
)


async def list_worlds(repos: Repositories, user_id: UserId) -> Sequence[World]:
    """Worlds the user owns or holds any permission grant in."""
    return await repos.worlds.list_for_user(user_id)


async def get_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> World:
    """The world, for a caller who owns it, holds any permission grant in it, or was invited to it.

    An invite - accepted or not - unlocks the world itself; entity-level access stays separate
    and must still be granted individually.
    """
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)

    if not permissions.is_owner(world, user_id):
        grants = await repos.permissions.get_grants(world_id, user_id)
        if not grants and await repos.invites.get_for_user(world_id, user_id) is None:
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


async def _delete_old_world_pic(
    storage: MediaStorage, world_id: WorldId, old_pic: str | None, new_pic: str | None
) -> None:
    """A world holds at most one pic - replacing or clearing it deletes the old file.

    No-ops if there was no previous pic, or it isn't one of our own media references (e.g.
    unset/placeholder data) - nothing to delete in either case.
    """
    if not old_pic or old_pic == new_pic:
        return

    old_file_id = extract_world_pic_file_id(old_pic, world_id)
    if old_file_id:
        await storage.delete_prefix(prefix=world_pic_key(world_id, old_file_id))


async def update_world(  # noqa: PLR0913, PLR0917 -- name/description/pic are the world's own mutable fields
    repos: Repositories,
    storage: MediaStorage,
    user_id: UserId,
    world_id: WorldId,
    name: str,
    description: str | None = None,
    pic: str | None = None,
) -> None:
    """Replaces the name/description/pic of the existing world. Ownership never changes through this call."""
    existing = await repos.worlds.get(world_id)
    if existing is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(existing, user_id):
        raise PermissionDeniedError(user_id, world_id)

    await _delete_old_world_pic(storage, world_id, existing.pic, pic)
    updated = existing.model_copy(update={"name": name, "description": description, "pic": pic})
    await repos.worlds.update(updated)


async def request_world_pic_upload(  # noqa: PLR0913 -- repos/storage/user_id/world_id distinct params
    repos: Repositories,
    storage: MediaStorage,
    user_id: UserId,
    world_id: WorldId,
    *,
    content_type: str,
    size: int,
    max_bytes: int,
    ttl_seconds: int,
) -> tuple[str, UploadPolicy]:
    """Mints a presigned upload policy for a world's pic. Returns (file_id, policy).

    Owner-only, same gate `update_world` uses to actually attach the uploaded file afterwards.
    """
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)

    return await mint_upload(
        storage,
        lambda file_id: world_pic_key(world_id, file_id),
        content_type=content_type,
        size=size,
        max_bytes=max_bytes,
        ttl_seconds=ttl_seconds,
    )


async def read_world_pic_redirect_url(  # noqa: PLR0913 -- repos/storage/user_id/world_id/file_id distinct params
    repos: Repositories, storage: MediaStorage, user_id: UserId, world_id: WorldId, file_id: str, *, ttl_seconds: int
) -> str:
    """Same read gate as `get_world`: owner, any permission grant, or an invite record (accepted or not)."""
    await get_world(repos, user_id, world_id)
    return await storage.generate_read_url(key=world_pic_key(world_id, file_id), ttl_seconds=ttl_seconds)


async def delete_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> None:
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)

    await repos.worlds.delete(world_id)


async def list_world_trash(repos: Repositories, user_id: UserId) -> Sequence[World]:
    """Soft-deleted worlds owned by the user - trash is owner-only, matching delete_world's gate."""
    return await repos.worlds.list_trash(user_id)


async def _require_trashed_world_owned_by(repos: Repositories, user_id: UserId, world_id: WorldId) -> World:
    world = await repos.worlds.get(world_id, include_deleted=True)
    if world is None:
        raise WorldNotFoundError(world_id)
    if not permissions.is_owner(world, user_id):
        raise PermissionDeniedError(user_id, world_id)
    if world.deleted_at is None:
        raise WorldNotInTrashError(world_id)
    return world


async def restore_world(repos: Repositories, user_id: UserId, world_id: WorldId) -> None:
    await _require_trashed_world_owned_by(repos, user_id, world_id)
    await repos.worlds.restore(world_id)


async def purge_world(repos: Repositories, storage: MediaStorage, user_id: UserId, world_id: WorldId) -> None:
    """Permanently deletes the world and every one of its entities - irreversible.

    Also deletes every one of those entities' media files, and the world's own pic prefix - once the
    rows are gone, nothing else would ever clean them up (unlike a plain `delete_world`, which leaves
    them orphaned).
    """
    await _require_trashed_world_owned_by(repos, user_id, world_id)
    purged_entity_ids = await repos.worlds.purge(world_id)
    for entity_id in purged_entity_ids:
        await storage.delete_prefix(prefix=entity_media_prefix(world_id, entity_id))
    await storage.delete_prefix(prefix=world_pic_prefix(world_id))
