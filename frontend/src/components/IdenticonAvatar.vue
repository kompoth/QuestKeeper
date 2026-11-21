<template>
  <v-avatar color="grey-lighten-3" :image="resolvedImage" :size="size" />
</template>

<script lang="ts" setup>
  import { toSvg } from 'jdenticon'
  import { computed } from 'vue'
  import { apiUrl } from '@/api/client'

  const props = withDefaults(defineProps<{
    seed: string
    size?: number
    // A bare, backend-relative avatar path (`User.avatar`) - resolved via `apiUrl()`. Falls back to
    // a generated identicon when null/undefined (no avatar set, or caller has no full `User`).
    avatarUrl?: string | null
  }>(), {
    size: 32,
    avatarUrl: null,
  })

  const dataUri = computed(() => `data:image/svg+xml;base64,${btoa(toSvg(props.seed, props.size))}`)
  const resolvedImage = computed(() => props.avatarUrl ? apiUrl(props.avatarUrl) : dataUri.value)
</script>
