<template>
  <v-menu>
    <template #activator="{ props: menuProps }">
      <slot name="activator" :props="menuProps" />
    </template>

    <v-list density="compact">
      <v-list-item
        v-if="currentUser?.role === 'admin'"
        prepend-icon="mdi-wizard-hat"
        title="Admin panel"
        to="/admin"
      />

      <v-list-item prepend-icon="mdi-account-cog" title="My Account" to="/account" />

      <v-list-item
        :prepend-icon="theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
        :title="theme.global.current.value.dark ? 'Light mode' : 'Dark mode'"
        @click="toggle"
      />

      <v-list-item prepend-icon="mdi-logout" title="Log out" @click="emit('logout')" />
    </v-list>
  </v-menu>
</template>

<script lang="ts" setup>
  import { useAuth } from '@/composables/useAuth'
  import { useThemeMode } from '@/composables/useThemeMode'

  const emit = defineEmits<{
    logout: []
  }>()

  const { currentUser } = useAuth()
  const { theme, toggle } = useThemeMode()
</script>
