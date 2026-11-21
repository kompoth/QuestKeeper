"""Entity-scoped media upload/read.

Upload: this backend only ever mints a presigned POST policy - the actual file bytes go straight
from the browser to the object store, never through this process.

Read: `GET .../media/{file_id}` is the stable path stored in article markdown / `Map.pic` (see
app.services.media). It never streams bytes either - it checks access, mints a fresh presigned GET,
and redirects.
"""

from collections.abc import Sequence

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import CurrentUser, MediaStorageDep, Repos, SettingsDep
from app.api.schemas import MediaItemOut, MediaUploadOut, RequestMediaUploadRequest
from app.domain.models import EntityId, WorldId
from app.services.media import delete_media, list_media, media_read_path, read_redirect_url, request_upload

router = APIRouter(prefix="/worlds/{world_id}/entities/{entity_id}/media", tags=["media"])


@router.post("")
async def upload(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    entity_id: EntityId,
    body: RequestMediaUploadRequest,
    user: CurrentUser,
    repos: Repos,
    storage: MediaStorageDep,
    settings: SettingsDep,
) -> MediaUploadOut:
    file_id, policy = await request_upload(
        repos,
        storage,
        user.id,
        world_id,
        entity_id,
        content_type=body.content_type,
        size=body.size,
        max_bytes=settings.media_max_upload_bytes,
        ttl_seconds=settings.media_presign_ttl_seconds,
    )
    return MediaUploadOut(file_id=file_id, url=policy.url, fields=policy.fields)


@router.get("/{file_id}")
async def read(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    entity_id: EntityId,
    file_id: str,
    user: CurrentUser,
    repos: Repos,
    storage: MediaStorageDep,
    settings: SettingsDep,
) -> RedirectResponse:
    url = await read_redirect_url(
        repos, storage, user.id, world_id, entity_id, file_id, ttl_seconds=settings.media_presign_ttl_seconds
    )
    # Bounded to the signed URL's own TTL, so a cached redirect never outlives the URL it points to.
    # `private`, not `public` - this is permission-gated content, so only the caller's own browser may cache it.
    headers = {"Cache-Control": f"private, max-age={settings.media_presign_ttl_seconds}"}
    return RedirectResponse(url, status_code=302, headers=headers)


@router.get("")
async def list_(
    world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos, storage: MediaStorageDep
) -> Sequence[MediaItemOut]:
    file_ids = await list_media(repos, storage, user.id, world_id, entity_id)
    return [MediaItemOut(file_id=file_id, path=media_read_path(world_id, entity_id, file_id)) for file_id in file_ids]


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId, entity_id: EntityId, file_id: str, user: CurrentUser, repos: Repos, storage: MediaStorageDep
) -> None:
    await delete_media(repos, storage, user.id, world_id, entity_id, file_id)
