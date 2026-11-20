<template>
  <NavBar app-subtitle="Pre-alpha" app-title="QuestKeeper" @logout="handleLogout">
    <template #sidebar>
      <v-list density="compact" nav>
        <v-list-item exact prepend-icon="mdi-earth" title="Worlds" to="/w" />
        <v-list-item prepend-icon="mdi-delete-restore" title="Trash" to="/w/trash" />
        <v-list-item disabled prepend-icon="mdi-cog" title="Settings" />
      </v-list>
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
  import NavBar from '@/components/NavBar.vue'
  import { useAuth } from '@/composables/useAuth'

  const router = useRouter()
  const { logout } = useAuth()

  async function handleLogout () {
    await logout()
    router.push('/login')
  }
</script>
