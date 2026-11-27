<template>
  <v-main>
    <v-container class="d-flex flex-column align-center justify-center" style="min-height: 100vh;">
      <h1 class="text-h4 mb-2">{{ item }} not found</h1>
      <v-icon class="mb-4" color="on-surface-variant" icon="mdi-compass-off-outline" size="92" />
      <v-btn color="primary" to="/w" variant="flat">Back to worlds</v-btn>
    </v-container>
  </v-main>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'

  const route = useRoute()
  const item = computed(() => (route.query.item as string | undefined) ?? 'Page')
</script>
