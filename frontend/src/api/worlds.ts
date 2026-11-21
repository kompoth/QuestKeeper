import type { World } from '@/types/world'
import { ApiError, apiFetch } from '@/api/client'
import { uploadToMintedPolicy } from '@/api/media'

interface WorldDto {
  id: string
  owner_id: string
  name: string
  description: string | null
  pic: string | null
  deleted_at: string | null
  owner_name?: string
}

function toWorld (dto: WorldDto): World {
  return {
    id: dto.id,
    ownerId: dto.owner_id,
    name: dto.name,
    description: dto.description,
    pic: dto.pic,
    deletedAt: dto.deleted_at,
    ownerName: dto.owner_name,
  }
}

export async function listWorlds (): Promise<World[]> {
  const dtos = await apiFetch<WorldDto[]>('/worlds')
  return dtos.map(dto => toWorld(dto))
}

export async function listWorldTrash (): Promise<World[]> {
  const dtos = await apiFetch<WorldDto[]>('/worlds/trash')
  return dtos.map(dto => toWorld(dto))
}

export async function getWorld (id: string): Promise<World | undefined> {
  try {
    return toWorld(await apiFetch<WorldDto>(`/worlds/${id}`))
  } catch (error) {
    // 403: caller has no access at all (no grant anywhere in the world) - same "unavailable" outcome as 404.
    if (error instanceof ApiError && (error.status === 404 || error.status === 403)) {
      return undefined
    }
    throw error
  }
}

export async function createWorld (name: string, description: string): Promise<World> {
  return toWorld(await apiFetch<WorldDto>('/worlds', { method: 'POST', body: { name, description } }))
}

export async function updateWorld (id: string, name: string, description: string, pic: string | null): Promise<World> {
  return toWorld(await apiFetch<WorldDto>(`/worlds/${id}`, { method: 'PATCH', body: { name, description, pic } }))
}

// A bare, backend-relative path, e.g. `/worlds/w1/pic/abc123` - not a usable URL on its own (no
// scheme/host), so it never expires and is safe to persist on `World.pic`. Resolve with `apiUrl()`
// from `@/api/client` wherever it's actually rendered.
export function worldPicPath (worldId: string, fileId: string): string {
  return `/worlds/${worldId}/pic/${fileId}`
}

// Uploads a new pic for a world and returns the stable reference to attach via `updateWorld`.
export async function uploadWorldPic (worldId: string, file: File): Promise<string> {
  const fileId = await uploadToMintedPolicy(`/worlds/${worldId}/pic`, file)
  return worldPicPath(worldId, fileId)
}

export async function deleteWorld (id: string): Promise<void> {
  await apiFetch<void>(`/worlds/${id}`, { method: 'DELETE' })
}

export async function restoreWorld (id: string): Promise<World> {
  return toWorld(await apiFetch<WorldDto>(`/worlds/${id}/restore`, { method: 'POST' }))
}

export async function purgeWorld (id: string): Promise<void> {
  await apiFetch<void>(`/worlds/${id}/purge`, { method: 'DELETE' })
}
