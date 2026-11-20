"""Entity-scoped media upload/read.

Upload: this backend only ever mints a presigned POST policy - the actual file bytes go straight
from the browser to the object store, never through this process.

Read: `GET .../media/{file_id}` is the stable path stored in article markdown / `Map.pic` (see
app.services.media). It never streams bytes either - it checks access, mints a fresh presigned GET,
and redirects.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.dependencies import CurrentUser, MediaStorageDep, Repos, SettingsDep, require_csrf
from app.api.schemas import MediaUploadOut, RequestMediaUploadRequest
from app.domain.models import EntityId, WorldId
from app.services.media import read_redirect_url, request_upload

router = APIRouter(prefix="/worlds/{world_id}/entities/{entity_id}/media", tags=["media"])


@router.post("", dependencies=[Depends(require_csrf)])
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
    return RedirectResponse(url, status_code=302)
