<template>
  <v-btn
    :icon="theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
    variant="text"
    @click="toggle"
  />
</template>

<script lang="ts" setup>
  import { useThemeMode } from '@/composables/useThemeMode'

  const { theme, toggle } = useThemeMode()
</script>
