/**
 * router/index.ts
 *
 * Manual routes for ./src/layouts/*.vue
 */

import { createRouter, createWebHistory } from 'vue-router'
import { getEntity } from '@/api/entities'
import { getWorld } from '@/api/worlds'
import { useAuth } from '@/composables/useAuth'
import Admin from '@/layouts/Admin.vue'
import Landing from '@/layouts/Landing.vue'
import Login from '@/layouts/Login.vue'
import NotFound from '@/layouts/NotFound.vue'
import World from '@/layouts/World.vue'
import Worlds from '@/layouts/Worlds.vue'
import AccountSettingsView from '@/views/account/AccountSettingsView.vue'
import AdminSettingsView from '@/views/admin/AdminSettingsView.vue'
import AdminUsersView from '@/views/admin/AdminUsersView.vue'
import LoginView from '@/views/login/LoginView.vue'
import PasswordRecoveryView from '@/views/login/PasswordRecoveryView.vue'
import ResetPasswordView from '@/views/login/ResetPasswordView.vue'
import EntityView from '@/views/world/EntityView.vue'
import AdvancedSettingsView from '@/views/world/settings/AdvancedSettingsView.vue'
import GeneralSettingsView from '@/views/world/settings/GeneralSettingsView.vue'
import MembersSettingsView from '@/views/world/settings/MembersSettingsView.vue'
import WorldsListView from '@/views/worlds/WorldsListView.vue'
import WorldsTrashView from '@/views/worlds/WorldsTrashView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
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
        {
          path: 'reset-password',
          component: ResetPasswordView,
        },
      ],
    },
    {
      path: '/w',
      component: Worlds,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          component: WorldsListView,
        },
        {
          path: 'trash',
          component: WorldsTrashView,
        },
      ],
    },
    {
      path: '/account',
      component: Worlds,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          component: AccountSettingsView,
        },
      ],
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
        {
          path: 'settings',
          beforeEnter: async to => {
            const world = await getWorld(to.params.worldId as string)
            const { currentUser } = useAuth()
            if (!world || world.ownerId !== currentUser.value?.id) {
              return { path: `/w/${to.params.worldId as string}` }
            }
          },
          children: [
            {
              path: '',
              redirect: to => `/w/${to.params.worldId as string}/settings/general`,
            },
            {
              path: 'general',
              component: GeneralSettingsView,
            },
            {
              path: 'members',
              component: MembersSettingsView,
            },
            {
              path: 'advanced',
              component: AdvancedSettingsView,
            },
          ],
        },
      ],
    },
    {
      path: '/admin',
      component: Admin,
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          redirect: '/admin/settings',
        },
        {
          path: 'settings',
          component: AdminSettingsView,
        },
        {
          path: 'users',
          component: AdminUsersView,
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

  if (to.meta.requiresAdmin && currentUser.value?.role !== 'admin') {
    return { path: '/w' }
  }

  if (to.path.startsWith('/login') && currentUser.value) {
    return { path: '/w' }
  }
})

export default router
