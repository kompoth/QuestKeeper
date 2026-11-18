import type { User, UserRole } from '@/types/user'
import { apiFetch } from '@/api/client'

interface UserDto {
  id: string
  name: string
  email: string
  role: UserRole
}

function toUser (dto: UserDto): User {
  return { id: dto.id, name: dto.name, email: dto.email, role: dto.role }
}

export async function login (email: string, password: string): Promise<User> {
  const dto = await apiFetch<UserDto>('/auth/login', { method: 'POST', body: { email, password } })
  return toUser(dto)
}

export async function logout (): Promise<void> {
  await apiFetch<null>('/auth/logout', { method: 'POST' })
}

export async function getCurrentUser (): Promise<User> {
  const dto = await apiFetch<UserDto>('/auth/me')
  return toUser(dto)
}
