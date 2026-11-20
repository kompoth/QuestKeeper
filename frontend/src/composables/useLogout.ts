import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

export function useLogout () {
  const router = useRouter()
  const { logout } = useAuth()

  async function handleLogout () {
    await logout()
    router.push('/login')
  }

  return { handleLogout }
}
