import type { User } from '@/types/user'
import { toUser, type UserDto } from '@/api/auth'
import { apiFetch } from '@/api/client'
import { uploadToMintedPolicy } from '@/api/media'

// Uploads a new avatar image and returns its file_id - this alone doesn't set it as the caller's
// avatar, call `setAvatar` with the result to do that.
export async function uploadAvatar (file: File): Promise<string> {
  return await uploadToMintedPolicy('/users/me/avatar/upload', file)
}

export async function setAvatar (fileId: string): Promise<User> {
  return toUser(await apiFetch<UserDto>('/users/me/avatar', { method: 'PUT', body: { file_id: fileId } }))
}

export async function clearAvatar (): Promise<User> {
  return toUser(await apiFetch<UserDto>('/users/me/avatar', { method: 'DELETE' }))
}
