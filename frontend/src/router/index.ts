/**
 * router/index.ts
 *
 * Manual routes for ./src/layouts/*.vue
 */

// Composables
import { createRouter, createWebHistory } from 'vue-router'
import Landing from '@/layouts/Landing.vue'
import Login from '@/layouts/Login.vue'
import World from '@/layouts/World.vue'
import Worlds from '@/layouts/Worlds.vue'
import LoginView from '@/views/login/LoginView.vue'
import PasswordRecoveryView from '@/views/login/PasswordRecoveryView.vue'
import EntityView from '@/views/world/EntityView.vue'

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
    },
    {
      path: '/w/:worldId',
      component: World,
      children: [
        {
          path: 'e/:entityId',
          component: EntityView,
        },
      ],
    },
  ],
})

export default router
