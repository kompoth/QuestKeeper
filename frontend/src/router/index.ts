/**
 * router/index.ts
 *
 * Manual routes for ./src/layouts/*.vue
 */

// Composables
import { createRouter, createWebHistory } from 'vue-router'
import { getEntity } from '@/api/entities'
import { getWorld } from '@/api/worlds'
import { useAuth } from '@/composables/useAuth'
import Landing from '@/layouts/Landing.vue'
import Login from '@/layouts/Login.vue'
import NotFound from '@/layouts/NotFound.vue'
import World from '@/layouts/World.vue'
import Worlds from '@/layouts/Worlds.vue'
import LoginView from '@/views/login/LoginView.vue'
import PasswordRecoveryView from '@/views/login/PasswordRecoveryView.vue'
import EntityView from '@/views/world/EntityView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: Landing,
    },
    {
      path: '/login',
      component: Login,
      children: [
        {
          path: '',
          component: LoginView,
        },
        {
          path: 'password-recovery',
          component: PasswordRecoveryView,
        },
      ],
    },
    {
      path: '/w',
      component: Worlds,
      meta: { requiresAuth: true },
    },
    {
      path: '/w/:worldId',
      component: World,
      meta: { requiresAuth: true },
      beforeEnter: async to => {
        if (!await getWorld(to.params.worldId as string)) {
          return { path: '/not-found', query: { item: 'World' } }
        }
      },
      children: [
        {
          path: 'e/:entityId',
          component: EntityView,
          beforeEnter: async to => {
            const entity = await getEntity(to.params.worldId as string, to.params.entityId as string)
            if (!entity) {
              return { path: '/not-found', query: { item: 'Entity' } }
            }
          },
        },
      ],
    },
    {
      path: '/not-found',
      component: NotFound,
    },
    {
      path: '/:pathMatch(.*)*',
      component: NotFound,
    },
  ],
})

router.beforeEach(async to => {
  const { currentUser, ensureChecked } = useAuth()

  if (to.meta.requiresAuth || to.path.startsWith('/login')) {
    await ensureChecked()
  }

  if (to.meta.requiresAuth && !currentUser.value) {
    return { path: '/login' }
  }

  if (to.path.startsWith('/login') && currentUser.value) {
    return { path: '/w' }
  }
})

export default router
