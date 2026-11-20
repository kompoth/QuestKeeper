"""Entity-scoped media upload/read, behind presigned S3 URLs.

A media file belongs to exactly one entity - reuse across entities isn't supported, matching the
same `get_entity_access` check already used for every other entity read/write. Reads never return a
signed URL directly: callers get a stable backend redirect path instead (see `media_read_path`),
which is what actually gets persisted in article markdown / `Map.pic` - the signed URL itself is
minted fresh on every hit to that route, never stored anywhere.
"""

import secrets
from collections.abc import Sequence

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
    """Mints a presigned upload policy for a new file on `entity_id`. Returns (file_id, policy).

    The content-type allow-list and size cap are both enforced for real by the signed POST's own
    conditions (fixed server-side values, baked into the policy below) - the checks here only give a
    clear, specific error before any upload is attempted, they aren't what actually stops anything.
    """
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    if content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise UnsupportedMediaTypeError(f"Unsupported file type '{content_type}'. Allowed: {allowed}")
    if size > max_bytes:
        raise MediaTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")

    file_id = secrets.token_urlsafe(9)
    policy = await storage.create_upload_policy(
        key=media_key(world_id, entity_id, file_id),
        content_type=content_type,
        max_bytes=max_bytes,
        ttl_seconds=ttl_seconds,
    )
    return file_id, policy


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
