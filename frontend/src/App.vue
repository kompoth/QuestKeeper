<template>
  <v-app>
    <router-view />
    <ConfirmDialog />
  </v-app>
</template>

<script lang="ts" setup>
  import ConfirmDialog from '@/components/ConfirmDialog.vue'
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
