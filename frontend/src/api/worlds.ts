import type { World } from '@/types/world'
import { ApiError, apiFetch } from '@/api/client'

interface WorldDto {
  id: string
  owner_id: string
  name: string
  description: string | null
  pic: string | null
  owner_name?: string
}

function toWorld (dto: WorldDto): World {
  return {
    id: dto.id,
    ownerId: dto.owner_id,
    name: dto.name,
    description: dto.description,
    pic: dto.pic,
    ownerName: dto.owner_name,
  }
}

export async function listWorlds (): Promise<World[]> {
  const dtos = await apiFetch<WorldDto[]>('/worlds')
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

export async function updateWorld (id: string, name: string, description: string): Promise<World> {
  return toWorld(await apiFetch<WorldDto>(`/worlds/${id}`, { method: 'PATCH', body: { name, description } }))
}

export async function deleteWorld (id: string): Promise<void> {
  await apiFetch<void>(`/worlds/${id}`, { method: 'DELETE' })
}
