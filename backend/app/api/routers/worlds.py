"""World listing, creation, and updates."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, MediaStorageDep, Repos, require_csrf
from app.api.schemas import CreateWorldRequest, UpdateWorldRequest, WorldOut
from app.domain.models import World, WorldId
from app.services.worlds import (
    create_world,
    delete_world,
    get_world,
    list_world_trash,
    list_worlds,
    purge_world,
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


@router.post("", dependencies=[Depends(require_csrf)])
async def create(body: CreateWorldRequest, user: CurrentUser, repos: Repos) -> World:
    world_id = await create_world(repos, user.id, body.name, body.description, body.pic)
    return await get_world(repos, user.id, world_id)


@router.get("/{world_id}")
async def get(world_id: WorldId, user: CurrentUser, repos: Repos) -> World:
    return await get_world(repos, user.id, world_id)


@router.patch("/{world_id}", dependencies=[Depends(require_csrf)])
async def update(world_id: WorldId, body: UpdateWorldRequest, user: CurrentUser, repos: Repos) -> World:
    await update_world(repos, user.id, world_id, body.name, body.description, body.pic)
    return await get_world(repos, user.id, world_id)


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def delete(world_id: WorldId, user: CurrentUser, repos: Repos) -> None:
    await delete_world(repos, user.id, world_id)


@router.post("/{world_id}/restore", dependencies=[Depends(require_csrf)])
async def restore(world_id: WorldId, user: CurrentUser, repos: Repos) -> World:
    await restore_world(repos, user.id, world_id)
    return await get_world(repos, user.id, world_id)


@router.delete("/{world_id}/purge", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def purge(world_id: WorldId, user: CurrentUser, repos: Repos, storage: MediaStorageDep) -> None:
    await purge_world(repos, storage, user.id, world_id)
