"""World listing, creation, and updates."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, Repos, require_csrf
from app.api.schemas import CreateWorldRequest, UpdateWorldRequest, WorldOut
from app.domain.models import World, WorldId
from app.services.worlds import create_world, delete_world, get_world, list_worlds, update_world

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.get("")
async def list_my_worlds(user: CurrentUser, repos: Repos) -> Sequence[WorldOut]:
    worlds = await list_worlds(repos, user.id)

    owners = {}
    for world in worlds:
        if world.owner_id not in owners:
            owners[world.owner_id] = await repos.users.get_by_id(world.owner_id)

    return [
        WorldOut(**world.model_dump(), owner_name=owner.name if (owner := owners[world.owner_id]) else "")
        for world in worlds
    ]


@router.post("", dependencies=[Depends(require_csrf)])
async def create(body: CreateWorldRequest, user: CurrentUser, repos: Repos) -> World:
    world_id = await create_world(repos, user.id, body.name, body.description, body.pic)
    return await get_world(repos, user.id, world_id)


@router.get("/{world_id}")
async def get(world_id: WorldId, user: CurrentUser, repos: Repos) -> World:
    return await get_world(repos, user.id, world_id)


@router.patch("/{world_id}", dependencies=[Depends(require_csrf)])
async def update(world_id: WorldId, body: UpdateWorldRequest, user: CurrentUser, repos: Repos) -> World:
    patch = World(id=world_id, owner_id="", name=body.name, description=body.description, pic=body.pic)
    await update_world(repos, user.id, patch)
    return await get_world(repos, user.id, world_id)


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def delete(world_id: WorldId, user: CurrentUser, repos: Repos) -> None:
    await delete_world(repos, user.id, world_id)
