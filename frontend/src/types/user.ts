export type UserRole = 'admin' | 'warden' | 'member'
export type UserStatus = 'active' | 'pending' | 'banned'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  status: UserStatus
  avatar: string | null
  joinedAt: string
}
