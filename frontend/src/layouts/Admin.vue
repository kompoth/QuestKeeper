<template>
  <NavBar app-title="Admin" show-back-button @logout="handleLogout">
    <template #sidebar>
      <AdminNav />
    </template>
  </NavBar>

  <v-main scrollable>
    <v-container>
      <router-view />
    </v-container>
  </v-main>
</template>

<script lang="ts" setup>
  import { useRouter } from 'vue-router'
  import AdminNav from '@/components/AdminNav.vue'
  import NavBar from '@/components/NavBar.vue'
  import { useAuth } from '@/composables/useAuth'

  const router = useRouter()
  const { logout } = useAuth()

  async function handleLogout () {
    await logout()
    router.push('/login')
  }
</script>
