"""Entity listing, creation, mutation, and article/map facets."""

from collections.abc import Sequence
from typing import TypedDict

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, MediaStorageDep, Repos
from app.api.schemas import (
    CreateEntityRequest,
    CreateMapPinRequest,
    EntityGrantOut,
    EntityOut,
    EntityPermissionsOut,
    InheritedEntityGrantOut,
    RenameEntityRequest,
    SetArticleRequest,
    SetMapRequest,
    UpdateMapPinRequest,
)
from app.domain.models import EntityId, MapPinId, PermissionLevel, User, UserId, WorldId
from app.domain.repositories import Repositories
from app.services.entities import (
    add_map_pin,
    clear_article,
    clear_map,
    create_entity,
    delete_entity,
    delete_map_pin,
    get_entity,
    list_entities,
    list_trash,
    purge_entity,
    rename_entity,
    restore_entity,
    restore_entity_branch,
    set_article,
    set_map,
    update_map_pin,
)
from app.services.sharing import EntityGrant, InheritedEntityGrant, get_entity_permissions

router = APIRouter(prefix="/worlds/{world_id}/entities", tags=["entities"])


async def _entity_out(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> EntityOut:
    entity, access = await get_entity(repos, user_id, world_id, entity_id)
    return EntityOut.from_entity(entity, access)


def _grantee_name(grantee: User, *, invite_accepted: bool | None) -> str | None:
    """None while this grantee has a not-yet-accepted invite to the world - revealing a name
    before they accept would leak that the email belongs to a known account."""
    return None if invite_accepted is False else grantee.name


@router.get("")
async def list_world_entities(world_id: WorldId, user: CurrentUser, repos: Repos) -> Sequence[EntityOut]:
    entities = await list_entities(repos, user.id, world_id)
    return [EntityOut.from_entity(entity, access) for entity, access in entities]


# Registered ahead of GET "/{entity_id}" below - that path pattern would otherwise swallow this one,
# treating "trash" as an entity_id.
@router.get("/trash")
async def list_world_trash(world_id: WorldId, user: CurrentUser, repos: Repos) -> Sequence[EntityOut]:
    entities = await list_trash(repos, user.id, world_id)
    return [EntityOut.from_entity(entity, access) for entity, access in entities]


@router.post("")
async def create(world_id: WorldId, body: CreateEntityRequest, user: CurrentUser, repos: Repos) -> EntityOut:
    entity_id = await create_entity(repos, user.id, world_id, body.parent_id, body.name)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.get("/{entity_id}")
async def get(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> EntityOut:
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.patch("/{entity_id}")
async def rename(
    world_id: WorldId, entity_id: EntityId, body: RenameEntityRequest, user: CurrentUser, repos: Repos
) -> EntityOut:
    await rename_entity(repos, user.id, world_id, entity_id, body.name)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> None:
    await delete_entity(repos, user.id, world_id, entity_id)


@router.post("/{entity_id}/restore")
async def restore(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> EntityOut:
    await restore_entity(repos, user.id, world_id, entity_id)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.post("/{entity_id}/restore-branch")
async def restore_branch(world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos) -> EntityOut:
    await restore_entity_branch(repos, user.id, world_id, entity_id)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge(
    world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos, storage: MediaStorageDep
) -> None:
    await purge_entity(repos, storage, user.id, world_id, entity_id)


@router.put("/{entity_id}/article")
async def put_article(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    entity_id: EntityId,
    body: SetArticleRequest,
    user: CurrentUser,
    repos: Repos,
    storage: MediaStorageDep,
) -> EntityOut:
    await set_article(repos, storage, user.id, world_id, entity_id, body.markdown)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}/article")
async def delete_article(
    world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos, storage: MediaStorageDep
) -> EntityOut:
    await clear_article(repos, storage, user.id, world_id, entity_id)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.put("/{entity_id}/map")
async def put_map(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    entity_id: EntityId,
    body: SetMapRequest,
    user: CurrentUser,
    repos: Repos,
    storage: MediaStorageDep,
) -> EntityOut:
    await set_map(repos, storage, user.id, world_id, entity_id, body.to_map())
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}/map")
async def delete_map(
    world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos, storage: MediaStorageDep
) -> EntityOut:
    await clear_map(repos, storage, user.id, world_id, entity_id)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.post("/{entity_id}/map/pins")
async def add_pin(
    world_id: WorldId, entity_id: EntityId, body: CreateMapPinRequest, user: CurrentUser, repos: Repos
) -> EntityOut:
    await add_map_pin(repos, user.id, world_id, entity_id, body.entity_id, body.x, body.y)
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.patch("/{entity_id}/map/pins/{pin_id}")
async def update_pin(  # noqa: PLR0913, PLR0917 -- distinct FastAPI-injected capability params, not data fields
    world_id: WorldId,
    entity_id: EntityId,
    pin_id: MapPinId,
    body: UpdateMapPinRequest,
    user: CurrentUser,
    repos: Repos,
) -> EntityOut:
    await update_map_pin(
        repos, user.id, world_id, entity_id, pin_id, x=body.x, y=body.y, pinned_entity_id=body.entity_id
    )
    return await _entity_out(repos, user.id, world_id, entity_id)


@router.delete("/{entity_id}/map/pins/{pin_id}")
async def delete_pin(
    world_id: WorldId, entity_id: EntityId, pin_id: MapPinId, user: CurrentUser, repos: Repos
) -> EntityOut:
    await delete_map_pin(repos, user.id, world_id, entity_id, pin_id)
    return await _entity_out(repos, user.id, world_id, entity_id)


class _GrantOutFields(TypedDict):
    user_id: UserId
    email: str
    name: str | None
    level: PermissionLevel


def _grant_out_fields(grant: EntityGrant | InheritedEntityGrant) -> _GrantOutFields:
    return _GrantOutFields(
        user_id=grant.user.id,
        email=grant.user.email,
        name=_grantee_name(grant.user, invite_accepted=grant.invite_accepted),
        level=grant.level,
    )


@router.get("/{entity_id}/permissions")
async def get_permissions(
    world_id: WorldId, entity_id: EntityId, user: CurrentUser, repos: Repos
) -> EntityPermissionsOut:
    view = await get_entity_permissions(repos, user.id, world_id, entity_id)
    return EntityPermissionsOut(
        direct=[EntityGrantOut(**_grant_out_fields(grant)) for grant in view.direct],
        inherited=[
            InheritedEntityGrantOut(**_grant_out_fields(grant), from_entity_id=grant.from_entity_id)
            for grant in view.inherited
        ],
    )
