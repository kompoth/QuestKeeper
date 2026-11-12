<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script lang="ts" setup>
  import { useThemeMode } from '@/composables/useThemeMode'

  useThemeMode().init()
</script>

<style>
html,
body {
  height: 100%;
  overflow: hidden;
}
</style>
