<template>
  <div ref="rootRef" class="entity-article" />
</template>

<script lang="ts" setup>
  import { Crepe } from '@milkdown/crepe'
  import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

  const saveIcon = '<span class="mdi mdi-content-save" style="font-size: 24px"></span>'

  const rootRef = ref<HTMLElement>()
  let crepe: Crepe | undefined

  onMounted(async () => {
    if (!rootRef.value) return

    crepe = new Crepe({
      root: rootRef.value,
      defaultValue: props.modelValue,
      features: {
        [Crepe.Feature.Latex]: false,
        [Crepe.Feature.CodeMirror]: false,
        [Crepe.Feature.Toolbar]: false,
        [Crepe.Feature.TopBar]: true,
      },
      featureConfigs: {
        [Crepe.Feature.TopBar]: {
          buildTopBar: builder => {
            builder.addGroup('save', 'Save').addItem('save', {
              icon: saveIcon,
              active: () => false,
              onRun: () => {
                // TODO: save entity
              },
            })
          },
        },
      },
    })

    crepe.on(listener => {
      listener.markdownUpdated((_ctx, markdown, prevMarkdown) => {
        if (markdown !== prevMarkdown) emit('update:modelValue', markdown)
      })
    })

    await crepe.create()
    crepe.setReadonly(!props.editable)
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
  --crepe-color-selected: rgba(var(--v-theme-primary), var(--v-selected-opacity));
  --crepe-color-inline-area: rgb(var(--v-theme-surface-light));
}
</style>
