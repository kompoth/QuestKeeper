<template>
  <div
    ref="viewportRef"
    class="map-viewport"
    :class="{ 'is-panning': panning }"
    @pointerdown="onPointerDown"
    @wheel.prevent="onWheel"
  >
    <div class="map-canvas" :style="{ transform: `translate(${x}px, ${y}px) scale(${scale})` }">
      <img
        ref="imageRef"
        alt=""
        class="map-image"
        draggable="false"
        :src="apiUrl(map.pic)"
        @load="onImageLoad"
      >

      <button
        v-for="pin in map.pins"
        :key="pin.entityId"
        class="map-marker"
        :style="{ left: `${pin.x}%`, top: `${pin.y}%` }"
        type="button"
        @click="emit('open', pin.entityId)"
      >
        <v-icon icon="mdi-compass-rose" size="64" />
      </button>
    </div>

    <v-sheet
      class="d-inline-flex ga-1 pa-1 align-center justify-center mx-auto map-controls"
      color="surface-light"
      rounded="pill"
    >
      <v-icon-btn icon="mdi-plus" size="small" variant="flat" @click="zoomIn" />
      <v-icon-btn icon="mdi-minus" size="small" variant="flat" @click="zoomOut" />
      <v-icon-btn icon="mdi-home" size="small" variant="flat" @click="resetZoom" />
    </v-sheet>
  </div>
</template>

<script lang="ts" setup>
  import type { EntityMapContent } from '@/types/entity'
  import { onBeforeUnmount, onMounted, ref } from 'vue'
  import { apiUrl } from '@/api/client'

  defineProps<{
    map: EntityMapContent
  }>()

  const emit = defineEmits<{
    open: [entityId: string]
  }>()

  const viewportRef = ref<HTMLElement>()
  const imageRef = ref<HTMLImageElement>()

  const scale = ref(1)
  const x = ref(0)
  const y = ref(0)
  const panning = ref(false)

  let minScale = 1
  let maxScale = 1
  let lastX = 0
  let lastY = 0

  function fitToViewport () {
    if (!viewportRef.value || !imageRef.value) return

    const { clientWidth, clientHeight } = viewportRef.value
    const { naturalWidth, naturalHeight } = imageRef.value
    const fitScale = Math.min(clientWidth / naturalWidth, clientHeight / naturalHeight, 1)

    minScale = fitScale
    maxScale = fitScale * 5
    scale.value = fitScale
    x.value = (clientWidth - naturalWidth * fitScale) / 2
    y.value = (clientHeight - naturalHeight * fitScale) / 2
  }

  function onImageLoad () {
    fitToViewport()
  }

  function onPointerMove (event: PointerEvent) {
    x.value += event.clientX - lastX
    y.value += event.clientY - lastY
    lastX = event.clientX
    lastY = event.clientY
  }

  function onPointerUp () {
    panning.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  }

  function onPointerDown (event: PointerEvent) {
    panning.value = true
    lastX = event.clientX
    lastY = event.clientY
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  function zoomBy (factor: number, originX: number, originY: number) {
    const localX = (originX - x.value) / scale.value
    const localY = (originY - y.value) / scale.value
    const nextScale = Math.min(maxScale, Math.max(minScale, scale.value * factor))

    x.value = originX - localX * nextScale
    y.value = originY - localY * nextScale
    scale.value = nextScale
  }

  function onWheel (event: WheelEvent) {
    if (!viewportRef.value) return

    const rect = viewportRef.value.getBoundingClientRect()
    const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1
    zoomBy(factor, event.clientX - rect.left, event.clientY - rect.top)
  }

  function zoomIn () {
    if (!viewportRef.value) return
    const { clientWidth, clientHeight } = viewportRef.value
    zoomBy(1.25, clientWidth / 2, clientHeight / 2)
  }

  function zoomOut () {
    if (!viewportRef.value) return
    const { clientWidth, clientHeight } = viewportRef.value
    zoomBy(1 / 1.25, clientWidth / 2, clientHeight / 2)
  }

  function resetZoom () {
    fitToViewport()
  }

  onMounted(() => {
    if (imageRef.value?.complete) fitToViewport()
  })

  onBeforeUnmount(() => {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  })
</script>

<style scoped>
.map-viewport {
  overflow: hidden;
  position: relative;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: grab;
}

.map-viewport.is-panning {
  cursor: grabbing;
}

.map-canvas {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
}

.map-image {
  display: block;
  max-width: none;
}

.map-marker {
  position: absolute;
  transform: translate(-50%, -100%);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

.map-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
