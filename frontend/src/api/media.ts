import { apiFetch } from '@/api/client'

interface MediaUploadDto {
  file_id: string
  url: string
  fields: Record<string, string>
}

interface MediaItemDto {
  file_id: string
  path: string
}

export interface MediaItem {
  fileId: string
  path: string
}

// A bare, backend-relative path, e.g. `/worlds/w1/entities/e1/media/abc123` - not a usable URL on
// its own (no scheme/host), so it never expires and is safe to persist (in article markdown or
// Map.pic). Resolve with `apiUrl()` from `@/api/client` wherever it's actually rendered.
export function mediaPath (worldId: string, entityId: string, fileId: string): string {
  return `/worlds/${worldId}/entities/${entityId}/media/${fileId}`
}

// Uploads a file for one entity's article/map and returns the stable reference to embed in
// content (see `mediaPath`). Throws ApiError for a mint-time rejection (unsupported type / too
// large / no access), or a plain Error if the direct-to-store upload itself fails (the store's own
// signed-condition check, e.g. a declared size that didn't match the real bytes).
export async function uploadMedia (worldId: string, entityId: string, file: File): Promise<string> {
  const mint = await apiFetch<MediaUploadDto>(`/worlds/${worldId}/entities/${entityId}/media`, {
    method: 'POST',
    body: { content_type: file.type, size: file.size },
  })

  const formData = new FormData()
  for (const [key, value] of Object.entries(mint.fields)) {
    formData.append(key, value)
  }
  formData.append('file', file)

  const uploadResponse = await fetch(mint.url, { method: 'POST', body: formData })
  if (!uploadResponse.ok) {
    throw new Error('Upload to storage failed')
  }

  return mediaPath(worldId, entityId, mint.file_id)
}

// Every file currently uploaded for this entity - the object store is the only source of truth
// for this (nothing in the database tracks it), so this always reflects real storage state.
export async function listMedia (worldId: string, entityId: string): Promise<MediaItem[]> {
  const dtos = await apiFetch<MediaItemDto[]>(`/worlds/${worldId}/entities/${entityId}/media`)
  return dtos.map(dto => ({ fileId: dto.file_id, path: dto.path }))
}

// Permanently deletes one file - nothing restores it, and any content still referencing it (article
// markdown, a Map's pic) is left pointing at a now-404ing path.
export async function deleteMedia (worldId: string, entityId: string, fileId: string): Promise<void> {
  await apiFetch<void>(`/worlds/${worldId}/entities/${entityId}/media/${fileId}`, { method: 'DELETE' })
}
