<template>
  <v-card :hover="to !== undefined" min-height="220" :to="to">
    <v-img v-if="world.pic" cover height="140" :src="apiUrl(world.pic)">
      <slot name="overlay" />
    </v-img>

    <v-sheet v-else class="d-flex align-center justify-center" color="surface-variant" height="140">
      <v-icon color="on-surface-variant" icon="mdi-image" size="48" />
      <slot name="overlay" />
    </v-sheet>

    <v-card-title>{{ world.name }}</v-card-title>
    <v-card-subtitle>{{ world.description }}</v-card-subtitle>

    <v-card-actions v-if="$slots.actions">
      <slot name="actions" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
  import type { World } from '@/types/world'
  import { apiUrl } from '@/api/client'

  defineProps<{
    world: World
    to?: string
  }>()
</script>
