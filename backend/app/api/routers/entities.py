"""Entity listing, creation, mutation, and article/map facets."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, Repos, require_csrf
from app.api.schemas import CreateEntityRequest, RenameEntityRequest, SetArticleRequest, SetMapRequest
from app.domain.models import Entity, EntityId, WorldId
from app.services.entities import (
    clear_article,
    clear_map,
    create_entity,
    delete_entity,
    get_entity,
    list_entities,
    rename_entity,
    set_article,
    set_map,
)

router = APIRouter(prefix="/worlds/{world_id}/entities", tags=["entities"])


@router.get("")
async def list_world_entities(world_id: WorldId, user: CurrentUser, repos: Repos) -> Sequence[Entity]:
    return await list_entities(repos, user.id, world_id)


@router.post("", dependencies=[Depends(require_csrf)])
async def create(world_id: WorldId, body: CreateEntityRequest, user: CurrentUser, repos: Repos) -> Entity:
    entity_id = await create_entity(repos, user.id, world_id, body.parent_id, body.name)
    return await get_entity(repos, user.id, world_id, entity_id)


@router.get("/{entity_id}")
async def get(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> Entity:
    return await get_entity(repos, user.id, world_id, entity_id)


@router.patch("/{entity_id}", dependencies=[Depends(require_csrf)])
async def rename(
    world_id: WorldId, entity_id: EntityId, body: RenameEntityRequest, user: CurrentUser, repos: Repos
) -> Entity:
    await rename_entity(repos, user.id, world_id, entity_id, body.name)
    return await get_entity(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def delete(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> None:
    await delete_entity(repos, user.id, world_id, entity_id)


@router.put("/{entity_id}/article", dependencies=[Depends(require_csrf)])
async def put_article(
    world_id: WorldId, entity_id: EntityId, body: SetArticleRequest, user: CurrentUser, repos: Repos
) -> Entity:
    await set_article(repos, user.id, world_id, entity_id, body.markdown)
    return await get_entity(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}/article", dependencies=[Depends(require_csrf)])
async def delete_article(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> Entity:
    await clear_article(repos, user.id, world_id, entity_id)
    return await get_entity(repos, user.id, world_id, entity_id)


@router.put("/{entity_id}/map", dependencies=[Depends(require_csrf)])
async def put_map(
    world_id: WorldId, entity_id: EntityId, body: SetMapRequest, user: CurrentUser, repos: Repos
) -> Entity:
    await set_map(repos, user.id, world_id, entity_id, body.to_map())
    return await get_entity(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}/map", dependencies=[Depends(require_csrf)])
async def delete_map(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> Entity:
    await clear_map(repos, user.id, world_id, entity_id)
    return await get_entity(repos, user.id, world_id, entity_id)
