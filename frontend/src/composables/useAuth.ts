import type { User } from '@/types/user'
import { ref } from 'vue'
import * as authApi from '@/api/auth'
import { ApiError } from '@/api/client'

const currentUser = ref<User | undefined>(undefined)
const checked = ref(false)

export function useAuth () {
  async function ensureChecked (): Promise<void> {
    if (checked.value) {
      return
    }
    try {
      currentUser.value = await authApi.getCurrentUser()
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        throw error
      }
      currentUser.value = undefined
    } finally {
      checked.value = true
    }
  }

  async function login (email: string, password: string): Promise<void> {
    currentUser.value = await authApi.login(email, password)
    checked.value = true
  }

  async function logout (): Promise<void> {
    await authApi.logout()
    currentUser.value = undefined
  }

  return { currentUser, ensureChecked, login, logout }
}
