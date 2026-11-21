"""Global, user-scoped avatar upload/read.

Upload: this backend only ever mints a presigned POST policy - the actual file bytes go straight
from the browser to the object store, never through this process.

Read: `GET /media/{file_id}` is the stable path stored on `User.avatar` (see app.services.avatar).
It never streams bytes either - it checks the caller is logged in, mints a fresh presigned GET, and
redirects.
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.dependencies import CurrentUser, MediaStorageDep, Repos, SettingsDep
from app.api.schemas import MediaUploadOut, RequestMediaUploadRequest, SetAvatarRequest, UserOut
from app.domain.models import User
from app.services.avatar import clear_avatar, read_avatar_redirect_url, request_avatar_upload, set_avatar

router = APIRouter(tags=["avatar"])


@router.post("/users/me/avatar/upload")
async def upload(
    body: RequestMediaUploadRequest,
    user: CurrentUser,  # noqa: ARG001 -- unused, only required to gate the route on being logged in
    storage: MediaStorageDep,
    settings: SettingsDep,
) -> MediaUploadOut:
    file_id, policy = await request_avatar_upload(
        storage,
        content_type=body.content_type,
        size=body.size,
        max_bytes=settings.media_max_upload_bytes,
        ttl_seconds=settings.media_presign_ttl_seconds,
    )
    return MediaUploadOut(file_id=file_id, url=policy.url, fields=policy.fields)


@router.get("/media/{file_id}")
async def read(
    file_id: str,
    user: CurrentUser,  # noqa: ARG001 -- unused, only required to gate the route on being logged in
    storage: MediaStorageDep,
    settings: SettingsDep,
) -> RedirectResponse:
    url = await read_avatar_redirect_url(storage, file_id, ttl_seconds=settings.media_presign_ttl_seconds)
    # Bounded to the signed URL's own TTL, so a cached redirect never outlives the URL it points to.
    # `private`, not `public` - only the caller's own browser may cache it.
    headers = {"Cache-Control": f"private, max-age={settings.media_presign_ttl_seconds}"}
    return RedirectResponse(url, status_code=302, headers=headers)


@router.put("/users/me/avatar", response_model=UserOut)
async def put_avatar(body: SetAvatarRequest, user: CurrentUser, repos: Repos, storage: MediaStorageDep) -> User:
    return await set_avatar(repos, storage, user.id, body.file_id)


@router.delete("/users/me/avatar", response_model=UserOut)
async def delete_avatar(user: CurrentUser, repos: Repos, storage: MediaStorageDep) -> User:
    return await clear_avatar(repos, storage, user.id)
