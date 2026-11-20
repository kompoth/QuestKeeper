<template>
  <div aria-label="Questkeeper" class="logo" role="img" v-html="svg" />
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import svg from '@/assets/logo-transparent.svg?raw'

  const props = withDefaults(defineProps<{
    size?: number
  }>(), {
    size: 36,
  })

  const sizePx = computed(() => `${props.size}px`)
</script>

<style scoped>
.logo {
  display: inline-flex;
}

.logo :deep(svg) {
  width: v-bind(sizePx);
  height: v-bind(sizePx);
}

:root[data-theme='dark'] .logo :deep(svg) {
  filter: invert(1);
}
</style>
