import type { RuntimeSettings } from '@/types/admin'
import type { User, UserRole, UserStatus } from '@/types/user'
import { toUser, type UserDto } from '@/api/auth'
import { apiFetch } from '@/api/client'

interface RuntimeSettingsDto {
  registration_enabled: boolean
  password_reset_enabled: boolean
}

function toRuntimeSettings (dto: RuntimeSettingsDto): RuntimeSettings {
  return { registrationEnabled: dto.registration_enabled, passwordResetEnabled: dto.password_reset_enabled }
}

export async function getRuntimeSettings (): Promise<RuntimeSettings> {
  return toRuntimeSettings(await apiFetch<RuntimeSettingsDto>('/admin/settings'))
}

export async function updateRuntimeSettings (settings: RuntimeSettings): Promise<RuntimeSettings> {
  const dto = await apiFetch<RuntimeSettingsDto>('/admin/settings', {
    method: 'PUT',
    body: { registration_enabled: settings.registrationEnabled, password_reset_enabled: settings.passwordResetEnabled },
  })
  return toRuntimeSettings(dto)
}

export async function listUsers (
  offset: number,
  limit: number,
  search?: string,
): Promise<{ users: User[], total: number }> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  if (search) {
    params.set('search', search)
  }
  const dto = await apiFetch<{ users: UserDto[], total: number }>(`/admin/users?${params}`)
  return { users: dto.users.map(userDto => toUser(userDto)), total: dto.total }
}

export async function changeUserRole (userId: string, role: UserRole): Promise<User> {
  return toUser(await apiFetch<UserDto>(`/admin/users/${userId}/role`, { method: 'PUT', body: { role } }))
}

export async function triggerPasswordReset (userId: string): Promise<void> {
  await apiFetch<void>(`/auth/admin/password-reset/${userId}`, { method: 'POST' })
}

export async function createUser (name: string, email: string, role: UserRole): Promise<User> {
  return toUser(await apiFetch<UserDto>('/admin/users', { method: 'POST', body: { name, email, role } }))
}

export async function changeUserStatus (userId: string, status: UserStatus): Promise<User> {
  return toUser(await apiFetch<UserDto>(`/admin/users/${userId}/status`, { method: 'PUT', body: { status } }))
}
