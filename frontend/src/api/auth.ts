import type { User, UserRole, UserStatus } from '@/types/user'
import { apiFetch } from '@/api/client'

export interface UserDto {
  id: string
  name: string
  email: string
  role: UserRole
  status: UserStatus
  avatar: string | null
  joined_at: string
}

export function toUser (dto: UserDto): User {
  return {
    id: dto.id,
    name: dto.name,
    email: dto.email,
    role: dto.role,
    status: dto.status,
    avatar: dto.avatar,
    joinedAt: dto.joined_at,
  }
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

export async function resetPassword (token: string, newPassword: string): Promise<void> {
  await apiFetch<null>('/auth/password-reset', { method: 'POST', body: { token, new_password: newPassword } })
}

export async function requestPasswordRecovery (email: string): Promise<void> {
  await apiFetch<null>('/auth/password-recovery', { method: 'POST', body: { email } })
}
