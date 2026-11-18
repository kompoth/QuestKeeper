export type UserRole = 'admin' | 'warden' | 'member'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
}
