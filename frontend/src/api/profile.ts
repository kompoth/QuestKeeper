import type { User } from '@/types/user'
import { toUser, type UserDto } from '@/api/auth'
import { apiFetch } from '@/api/client'

export async function updateName (name: string): Promise<User> {
  return toUser(await apiFetch<UserDto>('/users/me/name', { method: 'PUT', body: { name } }))
}
