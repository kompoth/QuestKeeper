"""World listing, creation, updates, and pic upload."""

from collections.abc import Sequence

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import CurrentUser, MediaStorageDep, Repos, SettingsDep
from app.api.schemas import CreateWorldRequest, MediaUploadOut, RequestMediaUploadRequest, UpdateWorldRequest, WorldOut
from app.domain.models import World, WorldId
from app.services.worlds import (
    create_world,
    delete_world,
    get_world,
    list_world_trash,
    list_worlds,
    purge_world,
    read_world_pic_redirect_url,
    request_world_pic_upload,
    restore_world,
    update_world,
)

router = APIRouter(prefix="/worlds", tags=["worlds"])


async def _with_owner_names(repos: Repos, worlds: Sequence[World]) -> list[WorldOut]:
    owners = {}
    for world in worlds:
        if world.owner_id not in owners:
            owners[world.owner_id] = await repos.users.get_by_id(world.owner_id)

    return [
        WorldOut(**world.model_dump(), owner_name=owner.name if (owner := owners[world.owner_id]) else "")
        for world in worlds
    ]


@router.get("")
async def list_my_worlds(user: CurrentUser, repos: Repos) -> Sequence[WorldOut]:
    worlds = await list_worlds(repos, user.id)
    return await _with_owner_names(repos, worlds)


# Registered ahead of GET "/{world_id}" below - that path pattern would otherwise swallow this one,
# treating "trash" as a world_id.
@router.get("/trash")
async def list_my_world_trash(user: CurrentUser, repos: Repos) -> Sequence[WorldOut]:
    worlds = await list_world_trash(repos, user.id)
    return await _with_owner_names(repos, worlds)


@router.post("")
async def create(body: CreateWorldRequest, user: CurrentUser, repos: Repos) -> World:
    world_id = await create_world(repos, user.id, body.name, body.description, body.pic)
    return await get_world(repos, user.id, world_id)


@router.get("/{world_id}")
async def get(world_id: WorldId, user: CurrentUser, repos: Repos) -> World:
    return await get_world(repos, user.id, world_id)


@router.patch("/{world_id}")
async def update(
    world_id: WorldId, body: UpdateWorldRequest, user: CurrentUser, repos: Repos, storage: MediaStorageDep
) -> World:
    await update_world(repos, storage, user.id, world_id, body.name, body.description, body.pic)
    return await get_world(repos, user.id, world_id)


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(world_id: WorldId, user: CurrentUser, repos: Repos) -> None:
    await delete_world(repos, user.id, world_id)


@router.post("/{world_id}/restore")
async def restore(world_id: WorldId, user: CurrentUser, repos: Repos) -> World:
    await restore_world(repos, user.id, world_id)
    return await get_world(repos, user.id, world_id)


@router.delete("/{world_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge(world_id: WorldId, user: CurrentUser, repos: Repos, storage: MediaStorageDep) -> None:
    await purge_world(repos, storage, user.id, world_id)


@router.post("/{world_id}/pic")
async def request_pic_upload(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    body: RequestMediaUploadRequest,
    user: CurrentUser,
    repos: Repos,
    storage: MediaStorageDep,
    settings: SettingsDep,
) -> MediaUploadOut:
    file_id, policy = await request_world_pic_upload(
        repos,
        storage,
        user.id,
        world_id,
        content_type=body.content_type,
        size=body.size,
        max_bytes=settings.media_max_upload_bytes,
        ttl_seconds=settings.media_presign_ttl_seconds,
    )
    return MediaUploadOut(file_id=file_id, url=policy.url, fields=policy.fields)


@router.get("/{world_id}/pic/{file_id}")
async def read_pic(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId, file_id: str, user: CurrentUser, repos: Repos, storage: MediaStorageDep, settings: SettingsDep
) -> RedirectResponse:
    url = await read_world_pic_redirect_url(
        repos, storage, user.id, world_id, file_id, ttl_seconds=settings.media_presign_ttl_seconds
    )
    headers = {"Cache-Control": f"private, max-age={settings.media_presign_ttl_seconds}"}
    return RedirectResponse(url, status_code=302, headers=headers)
