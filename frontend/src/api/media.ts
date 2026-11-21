import { apiFetch } from '@/api/client'

interface MediaUploadDto {
  file_id: string
  url: string
  fields: Record<string, string>
}

// A bare, backend-relative path, e.g. `/worlds/w1/entities/e1/media/abc123` - not a usable URL on
// its own (no scheme/host), so it never expires and is safe to persist (in article markdown or
// Map.pic). Resolve with `apiUrl()` from `@/api/client` wherever it's actually rendered.
export function mediaPath (worldId: string, entityId: string, fileId: string): string {
  return `/worlds/${worldId}/entities/${entityId}/media/${fileId}`
}

// Mints an upload policy at `mintPath` and uploads `file` directly to the object store. Returns the
// minted file_id, for the caller to build its own stable path from (see `mediaPath` and friends).
// Shared by every upload surface (entity media, avatars, world pics) - only the mint path and the
// resulting path shape differ between them.
//
// Throws ApiError for a mint-time rejection (unsupported type / too large / no access), or a plain
// Error if the direct-to-store upload itself fails (the store's own signed-condition check, e.g. a
// declared size that didn't match the real bytes).
export async function uploadToMintedPolicy (mintPath: string, file: File): Promise<string> {
  const mint = await apiFetch<MediaUploadDto>(mintPath, {
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

  return mint.file_id
}

// Uploads a file for one entity's article/map and returns the stable reference to embed in
// content (see `mediaPath`).
export async function uploadMedia (worldId: string, entityId: string, file: File): Promise<string> {
  const fileId = await uploadToMintedPolicy(`/worlds/${worldId}/entities/${entityId}/media`, file)
  return mediaPath(worldId, entityId, fileId)
}
