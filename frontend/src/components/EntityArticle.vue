<template>
  <div ref="rootRef" :class="{ 'article-mobile': mobile }" />
</template>

<script lang="ts" setup>
  import { Crepe } from '@milkdown/crepe'
  import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { useDisplay } from 'vuetify'
  import '@milkdown/crepe/theme/common/style.css'
  import '@milkdown/crepe/theme/frame.css'

  const props = withDefaults(defineProps<{
    modelValue: string
    editable?: boolean
  }>(), {
    editable: false,
  })

  const emit = defineEmits<{
    'update:modelValue': [value: string]
  }>()

  const rootRef = ref<HTMLElement>()
  const { mobile } = useDisplay()
  let crepe: Crepe | undefined

  function featuresFor (isMobile: boolean) {
    return {
      [Crepe.Feature.Latex]: false,
      [Crepe.Feature.CodeMirror]: false,
      // The drag-handle/block menu and floating toolbar don't suit touch input - a persistent top bar
      // covers the same formatting actions without needing a hover or a text selection to appear.
      ...isMobile
        ? { [Crepe.Feature.BlockEdit]: false, [Crepe.Feature.Toolbar]: false, [Crepe.Feature.TopBar]: true }
        : {},
    }
  }

  async function createEditor (defaultValue: string) {
    if (!rootRef.value) return

    crepe = new Crepe({
      root: rootRef.value,
      defaultValue,
      features: featuresFor(mobile.value),
    })

    crepe.on(listener => {
      listener.markdownUpdated((_ctx, markdown, prevMarkdown) => {
        if (markdown !== prevMarkdown) emit('update:modelValue', markdown)
      })
    })

    await crepe.create()
    crepe.setReadonly(!props.editable)
  }

  onMounted(() => createEditor(props.modelValue))

  // Crepe's feature set is constructor-only (no runtime toggle), so crossing the mobile breakpoint
  // needs a full rebuild - re-seeded from the live editor content, not the (possibly stale, debounced)
  // modelValue prop, so nothing typed since the last autosave is lost.
  watch(mobile, async () => {
    const markdown = crepe?.getMarkdown() ?? props.modelValue
    crepe?.destroy()
    await createEditor(markdown)
  })

  watch(() => props.editable, editable => {
    crepe?.setReadonly(!editable)
  })

  onBeforeUnmount(() => {
    crepe?.destroy()
  })
</script>

<style>
.milkdown {
  /* Background Colors */
  --crepe-color-background: rgb(var(--v-theme-background));
  --crepe-color-surface: rgb(var(--v-theme-surface));
  --crepe-color-surface-low: rgb(var(--v-theme-surface-light));

  /* Text Colors */
  --crepe-color-on-background: rgb(var(--v-theme-on-background));
  --crepe-color-on-surface: rgb(var(--v-theme-on-surface));
  --crepe-color-on-surface-variant: rgb(var(--v-theme-on-surface-variant));

  /* Accent Colors */
  --crepe-color-primary: rgb(var(--v-theme-primary));
  --crepe-color-secondary: rgb(var(--v-theme-secondary));
  --crepe-color-on-secondary: rgb(var(--v-theme-on-secondary));

  /* UI Colors */
  --crepe-color-outline: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  --crepe-color-inverse: rgb(var(--v-theme-surface-variant));
  --crepe-color-on-inverse: rgb(var(--v-theme-on-surface-variant));
  --crepe-color-inline-code: rgb(var(--v-theme-error));
  --crepe-color-error: rgb(var(--v-theme-error));

  /* Interactive Colors */
  --crepe-color-hover: rgba(var(--v-theme-on-surface), var(--v-hover-opacity));
  --crepe-color-selected: rgba(var(--v-theme-primary), 0.5);
  --crepe-color-inline-area: rgb(var(--v-theme-surface-light));
}

/* Crepe's base theme hardcodes 60px/120px regardless of viewport - way too wide a gutter on a phone. */
.article-mobile .milkdown .ProseMirror {
  padding: 24px 16px;
}
</style>
