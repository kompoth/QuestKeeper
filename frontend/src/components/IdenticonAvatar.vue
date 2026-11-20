<template>
  <v-avatar color="grey-lighten-3" :image="dataUri" :size="size" />
</template>

<script lang="ts" setup>
  import { toSvg } from 'jdenticon'
  import { computed } from 'vue'

  const props = withDefaults(defineProps<{
    seed: string
    size?: number
  }>(), {
    size: 32,
  })

  const dataUri = computed(() => `data:image/svg+xml;base64,${btoa(toSvg(props.seed, props.size))}`)
</script>
