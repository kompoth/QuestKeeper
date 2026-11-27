import type { EntityGrant, EntityPermissions, InheritedEntityGrant, PermissionLevel } from '@/types/permission'
import { apiFetch } from '@/api/client'

interface EntityGrantDto {
  user_id: string
  email: string
  name: string | null
  level: PermissionLevel
}

interface InheritedEntityGrantDto extends EntityGrantDto {
  from_entity_id: string
}

interface EntityPermissionsDto {
  direct: EntityGrantDto[]
  inherited: InheritedEntityGrantDto[]
}

function toGrant (dto: EntityGrantDto): EntityGrant {
  return { userId: dto.user_id, email: dto.email, name: dto.name, level: dto.level }
}

function toInheritedGrant (dto: InheritedEntityGrantDto): InheritedEntityGrant {
  return { ...toGrant(dto), fromEntityId: dto.from_entity_id }
}

export async function getEntityPermissions (worldId: string, entityId: string): Promise<EntityPermissions> {
  const dto = await apiFetch<EntityPermissionsDto>(`/worlds/${worldId}/entities/${entityId}/permissions`)
  return {
    direct: dto.direct.map(grant => toGrant(grant)),
    inherited: dto.inherited.map(grant => toInheritedGrant(grant)),
  }
}

export async function grantPermission (
  worldId: string, entityId: string, granteeEmail: string, level: PermissionLevel,
): Promise<void> {
  await apiFetch<void>(`/worlds/${worldId}/permissions`, {
    method: 'POST',
    body: { entity_id: entityId, grantee_email: granteeEmail, level },
  })
}

export async function revokePermission (worldId: string, granteeId: string, entityId: string): Promise<void> {
  await apiFetch<void>(`/worlds/${worldId}/permissions/${granteeId}/${entityId}`, { method: 'DELETE' })
}
