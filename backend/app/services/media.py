"""Entity- and world-scoped media key shapes, plus the shared upload-minting logic.

A media file belongs to exactly one entity (or, for a world's pic, one world) - reuse across owners
isn't supported, matching the same access check already used for every other read/write of that
owner. Reads never return a signed URL directly: callers get a stable backend redirect path instead
(see `media_read_path`/`world_pic_read_path`), which is what actually gets persisted in article
markdown / `Map.pic` / `World.pic` - the signed URL itself is minted fresh on every hit to that
route, never stored anywhere.
"""

import secrets
from collections.abc import Callable, Sequence

from app.domain.media import MediaStorage, UploadPolicy
from app.domain.models import EntityId, UserId, WorldId
from app.domain.repositories import Repositories
from app.services.access import get_entity_access
from app.services.errors import MediaTooLargeError, PermissionDeniedError, UnsupportedMediaTypeError

ALLOWED_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})


def media_key(world_id: WorldId, entity_id: EntityId, file_id: str) -> str:
    return f"worlds/{world_id}/entities/{entity_id}/{file_id}"


def entity_media_prefix(world_id: WorldId, entity_id: EntityId) -> str:
    return f"worlds/{world_id}/entities/{entity_id}/"


def media_read_path(world_id: WorldId, entity_id: EntityId, file_id: str) -> str:
    """The stable, non-expiring path stored in content - not a signed URL, never rewritten."""
    return f"/worlds/{world_id}/entities/{entity_id}/media/{file_id}"


def extract_media_file_id(reference: str, world_id: WorldId, entity_id: EntityId) -> str | None:
    """The file_id embedded in a `media_read_path()`-shaped reference, or None if it isn't one.

    Used to find the old file to delete when a `Map`'s single image is replaced - returns None for
    anything that isn't our own reference shape (e.g. mock/placeholder data), so callers can skip
    deletion safely rather than guess.
    """
    prefix = media_read_path(world_id, entity_id, "")
    return reference.removeprefix(prefix) if reference.startswith(prefix) else None


def world_pic_key(world_id: WorldId, file_id: str) -> str:
    return f"worlds/{world_id}/pic/{file_id}"


def world_pic_prefix(world_id: WorldId) -> str:
    return f"worlds/{world_id}/pic/"


def world_pic_read_path(world_id: WorldId, file_id: str) -> str:
    """The stable, non-expiring path stored on `World.pic` - not a signed URL, never rewritten."""
    return f"/worlds/{world_id}/pic/{file_id}"


def extract_world_pic_file_id(reference: str, world_id: WorldId) -> str | None:
    """The file_id embedded in a `world_pic_read_path()`-shaped reference, or None if it isn't one.

    Used to find the old pic to delete when a world's pic is replaced - returns None for anything
    that isn't our own reference shape (e.g. mock/placeholder data), so callers can skip deletion
    safely rather than guess.
    """
    prefix = world_pic_read_path(world_id, "")
    return reference.removeprefix(prefix) if reference.startswith(prefix) else None


async def mint_upload(  # noqa: PLR0913 -- storage/key_builder/content_type/size/max_bytes/ttl_seconds distinct params
    storage: MediaStorage,
    key_builder: Callable[[str], str],
    *,
    content_type: str,
    size: int,
    max_bytes: int,
    ttl_seconds: int,
) -> tuple[str, UploadPolicy]:
    """Mints a presigned upload policy for a new file_id, keyed via `key_builder(file_id)`.

    Shared by every media upload surface (entity media, avatars, world pics) - only the key shape
    and the caller's own access check differ between them.

    The content-type allow-list and size cap are both enforced for real by the signed POST's own
    conditions (fixed server-side values, baked into the policy below) - the checks here only give a
    clear, specific error before any upload is attempted, they aren't what actually stops anything.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise UnsupportedMediaTypeError(f"Unsupported file type '{content_type}'. Allowed: {allowed}")
    if size > max_bytes:
        raise MediaTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")

    file_id = secrets.token_urlsafe(9)
    policy = await storage.create_upload_policy(
        key=key_builder(file_id), content_type=content_type, max_bytes=max_bytes, ttl_seconds=ttl_seconds
    )
    return file_id, policy


async def request_upload(  # noqa: PLR0913 -- repos/storage/world_id/entity_id distinct params, not data fields
    repos: Repositories,
    storage: MediaStorage,
    user_id: UserId,
    world_id: WorldId,
    entity_id: EntityId,
    *,
    content_type: str,
    size: int,
    max_bytes: int,
    ttl_seconds: int,
) -> tuple[str, UploadPolicy]:
    """Mints a presigned upload policy for a new file on `entity_id`. Returns (file_id, policy)."""
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    return await mint_upload(
        storage,
        lambda file_id: media_key(world_id, entity_id, file_id),
        content_type=content_type,
        size=size,
        max_bytes=max_bytes,
        ttl_seconds=ttl_seconds,
    )


async def read_redirect_url(  # noqa: PLR0913, PLR0917 -- repos/storage/world_id/entity_id distinct params
    repos: Repositories,
    storage: MediaStorage,
    user_id: UserId,
    world_id: WorldId,
    entity_id: EntityId,
    file_id: str,
    *,
    ttl_seconds: int,
) -> str:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.read:
        raise PermissionDeniedError(user_id, entity_id)

    return await storage.generate_read_url(key=media_key(world_id, entity_id, file_id), ttl_seconds=ttl_seconds)


async def list_media(
    repos: Repositories, storage: MediaStorage, user_id: UserId, world_id: WorldId, entity_id: EntityId
) -> Sequence[str]:
    """Every file_id currently uploaded under this entity - the object store is the only source of
    truth for this (nothing in the database tracks it), so this always reflects real storage state."""
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.read:
        raise PermissionDeniedError(user_id, entity_id)

    prefix = entity_media_prefix(world_id, entity_id)
    keys = await storage.list_objects(prefix=prefix)
    return [key.removeprefix(prefix) for key in keys]


async def delete_media(  # noqa: PLR0913, PLR0917 -- repos/storage/world_id/entity_id distinct params
    repos: Repositories, storage: MediaStorage, user_id: UserId, world_id: WorldId, entity_id: EntityId, file_id: str
) -> None:
    """Permanently deletes one file - nothing else ever restores it, and any content still
    referencing it (article markdown, a Map's pic) is left pointing at a now-404ing path."""
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    await storage.delete_prefix(prefix=media_key(world_id, entity_id, file_id))
