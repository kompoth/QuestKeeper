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
  import AdminNav from '@/components/AdminNav.vue'
  import NavBar from '@/components/NavBar.vue'
  import { useLogout } from '@/composables/useLogout'

  const { handleLogout } = useLogout()
</script>
