import type { Entity } from '@/types/entity'
import { ApiError, apiFetch } from '@/api/client'

interface MapPinDto {
  entity_id: string
  x: number
  y: number
}

interface EntityAccessDto {
  read: boolean
  write: boolean
  can_delete: boolean
}

interface EntityDto {
  id: string
  world_id: string
  name: string
  parent: string | null
  children: string[]
  article: { markdown: string } | null
  map: { pic: string, pins: Record<string, MapPinDto> } | null
  created_at: string | null
  updated_at: string | null
  created_by: string | null
  updated_by: string | null
  access: EntityAccessDto
}

function toEntity (dto: EntityDto): Entity {
  return {
    id: dto.id,
    worldId: dto.world_id,
    name: dto.name,
    parent: dto.parent,
    children: dto.children,
    article: dto.article,
    map: dto.map === null
      ? null
      : {
          pic: dto.map.pic,
          pins: Object.values(dto.map.pins).map(pin => ({ entityId: pin.entity_id, x: pin.x, y: pin.y })),
        },
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    createdBy: dto.created_by,
    updatedBy: dto.updated_by,
    access: { read: dto.access.read, write: dto.access.write, canDelete: dto.access.can_delete },
  }
}

export async function listEntities (worldId: string): Promise<Entity[]> {
  const dtos = await apiFetch<EntityDto[]>(`/worlds/${worldId}/entities`)
  return dtos.map(dto => toEntity(dto))
}

export async function getEntity (worldId: string, entityId: string): Promise<Entity | undefined> {
  try {
    return toEntity(await apiFetch<EntityDto>(`/worlds/${worldId}/entities/${entityId}`))
  } catch (error) {
    // 403: an ancestor the caller lacks read access to (e.g. walking a breadcrumb path) - same "unavailable" outcome as 404.
    if (error instanceof ApiError && (error.status === 404 || error.status === 403)) {
      return undefined
    }
    throw error
  }
}

export async function createEntity (worldId: string, name: string, parentId?: string): Promise<Entity> {
  const dto = await apiFetch<EntityDto>(`/worlds/${worldId}/entities`, {
    method: 'POST',
    body: { name, parent_id: parentId ?? null },
  })
  return toEntity(dto)
}

export async function renameEntity (worldId: string, entityId: string, name: string): Promise<Entity> {
  const dto = await apiFetch<EntityDto>(`/worlds/${worldId}/entities/${entityId}`, { method: 'PATCH', body: { name } })
  return toEntity(dto)
}

export async function deleteEntity (worldId: string, entityId: string): Promise<void> {
  await apiFetch<null>(`/worlds/${worldId}/entities/${entityId}`, { method: 'DELETE' })
}

export async function setArticle (worldId: string, entityId: string, markdown: string): Promise<Entity> {
  const dto = await apiFetch<EntityDto>(`/worlds/${worldId}/entities/${entityId}/article`, {
    method: 'PUT',
    body: { markdown },
  })
  return toEntity(dto)
}
