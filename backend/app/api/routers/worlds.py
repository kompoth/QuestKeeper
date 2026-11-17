"""World listing, creation, and updates."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, Repos, require_csrf
from app.api.schemas import CreateWorldRequest, UpdateWorldRequest
from app.domain.models import World, WorldId
from app.services.worlds import create_world, get_world, list_worlds, update_world

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.get("")
async def list_my_worlds(user: CurrentUser, repos: Repos) -> Sequence[World]:
    return await list_worlds(repos, user.id)


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
