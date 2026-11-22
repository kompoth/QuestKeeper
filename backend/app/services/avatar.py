"""Global, user-scoped avatar upload/read, behind presigned S3 URLs.

Unlike entity media, a global-media file isn't owned by any world/entity - the read gate is just
"logged in", since an avatar is shown wherever its owner is named across the app (member lists,
admin tables, etc). Setting/clearing is restricted to the caller's own avatar, enforced simply by
there being no other user id this module ever takes - there's no "set someone else's avatar".
"""

from app.domain.media import MediaStorage, UploadPolicy
from app.domain.models import User, UserId
from app.domain.repositories import Repositories
from app.services.errors import UserNotFoundError
from app.services.media import mint_upload


def global_media_key(file_id: str) -> str:
    return f"global/{file_id}"


def avatar_read_path(file_id: str) -> str:
    """The stable, non-expiring path stored on `User.avatar` - not a signed URL, never rewritten."""
    return f"/api/media/{file_id}"


def extract_avatar_file_id(reference: str) -> str | None:
    """The file_id embedded in an `avatar_read_path()`-shaped reference, or None if it isn't one.

    Used to find the old avatar to delete when a user's avatar is replaced - returns None for
    anything that isn't our own reference shape (e.g. unset data), so callers can skip deletion
    safely rather than guess.
    """
    prefix = avatar_read_path("")
    return reference.removeprefix(prefix) if reference.startswith(prefix) else None


async def request_avatar_upload(
    storage: MediaStorage, *, content_type: str, size: int, max_bytes: int, ttl_seconds: int
) -> tuple[str, UploadPolicy]:
    """Mints a presigned upload policy for a new global-media file. Returns (file_id, policy).

    No access check beyond being logged in, which `CurrentUser` already enforces at the route.
    """
    return await mint_upload(
        storage, global_media_key, content_type=content_type, size=size, max_bytes=max_bytes, ttl_seconds=ttl_seconds
    )


async def read_avatar_redirect_url(storage: MediaStorage, file_id: str, *, ttl_seconds: int) -> str:
    """Any logged-in user may read any global-media file - `CurrentUser` is the only gate."""
    return await storage.generate_read_url(key=global_media_key(file_id), ttl_seconds=ttl_seconds)


async def _delete_old_avatar(storage: MediaStorage, old_avatar: str | None, new_avatar: str | None) -> None:
    """A user holds at most one avatar - replacing or clearing it deletes the old file.

    No-ops if there was no previous avatar, or it isn't one of our own media references.
    """
    if not old_avatar or old_avatar == new_avatar:
        return

    old_file_id = extract_avatar_file_id(old_avatar)
    if old_file_id:
        await storage.delete_prefix(prefix=global_media_key(old_file_id))


async def set_avatar(repos: Repositories, storage: MediaStorage, user_id: UserId, file_id: str) -> User:
    """Sets the caller's own avatar to `file_id`, deleting the previous one's object first."""
    user = await repos.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)

    new_avatar = avatar_read_path(file_id)
    await _delete_old_avatar(storage, user.avatar, new_avatar)
    await repos.users.update_avatar(user_id, new_avatar)
    return user.model_copy(update={"avatar": new_avatar})


async def clear_avatar(repos: Repositories, storage: MediaStorage, user_id: UserId) -> User:
    """Clears the caller's own avatar, deleting its underlying object."""
    user = await repos.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)

    await _delete_old_avatar(storage, user.avatar, None)
    await repos.users.update_avatar(user_id, None)
    return user.model_copy(update={"avatar": None})
