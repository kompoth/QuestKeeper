<template>
  <div
    ref="viewportRef"
    class="map-viewport"
    :class="{ 'is-panning': panning, 'is-editable': editable }"
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

      <v-tooltip
        v-for="pin in map.pins"
        :key="pin.id"
        location="top"
        :model-value="hoveredPinId === pin.id"
        :text="pinLabel(pin)"
        @update:model-value="open => handleTooltipUpdate(pin.id, open)"
      >
        <template #activator="{ props: tooltipProps }">
          <button
            class="map-marker"
            :class="{ 'map-marker--orphan': isOrphan(pin), 'map-marker--inert': isOrphan(pin) && !editable }"
            :style="pinStyle(pin)"
            type="button"
            v-bind="tooltipProps"
            @click="onPinClick(pin)"
            @pointerdown="onPinPointerDown($event, pin)"
          >
            <v-icon color="primary" icon="mdi-map-marker" size="64" />
          </button>
        </template>
      </v-tooltip>
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
  import type { EntityMapContent, MapPin } from '@/types/entity'
  import { onBeforeUnmount, onMounted, ref } from 'vue'
  import { apiUrl } from '@/api/client'

  const CLICK_THRESHOLD_PX = 6

  const props = defineProps<{
    map: EntityMapContent
    editable?: boolean
    validEntityIds?: Set<string>
    entityNames?: Map<string, string>
  }>()

  const emit = defineEmits<{
    'open': [entityId: string]
    'canvas-click': [x: number, y: number]
    'pin-click': [pinId: string]
    'pin-move': [pinId: string, x: number, y: number]
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
  let downX = 0
  let downY = 0

  function isOrphan (pin: MapPin): boolean {
    return props.validEntityIds !== undefined && !props.validEntityIds.has(pin.entityId)
  }

  function pinLabel (pin: MapPin): string {
    return props.entityNames?.get(pin.entityId) ?? 'Unknown entity'
  }

  // A tooltip's position is computed once when it opens - zooming moves the pin under it without
  // firing any event the tooltip would reposition on, so it'd otherwise drift. Closing it on every
  // zoom change (see zoomBy/fitToViewport) is simpler than chasing a live reposition.
  const hoveredPinId = ref<string>()

  function handleTooltipUpdate (pinId: string, open: boolean) {
    if (open) {
      hoveredPinId.value = pinId
    } else if (hoveredPinId.value === pinId) {
      hoveredPinId.value = undefined
    }
  }

  const draggingPinId = ref<string>()
  const dragPosition = ref<{ x: number, y: number }>()

  function pinStyle (pin: MapPin) {
    const pos = pin.id === draggingPinId.value && dragPosition.value ? dragPosition.value : pin
    return { left: `${pos.x}%`, top: `${pos.y}%` }
  }

  function percentFromPointer (event: PointerEvent): { x: number, y: number } | undefined {
    if (!imageRef.value) return undefined
    const rect = imageRef.value.getBoundingClientRect()
    const px = ((event.clientX - rect.left) / rect.width) * 100
    const py = ((event.clientY - rect.top) / rect.height) * 100
    return { x: Math.min(100, Math.max(0, px)), y: Math.min(100, Math.max(0, py)) }
  }

  function onPinClick (pin: MapPin) {
    if (props.editable) return // edit-mode interaction is fully handled by the pointerdown/up drag logic below
    if (isOrphan(pin)) return
    emit('open', pin.entityId)
  }

  function onPinPointerDown (event: PointerEvent, pin: MapPin) {
    if (!props.editable) return
    event.stopPropagation() // don't also start a canvas pan

    draggingPinId.value = pin.id
    dragPosition.value = { x: pin.x, y: pin.y }
    downX = event.clientX
    downY = event.clientY
    window.addEventListener('pointermove', onPinPointerMove)
    window.addEventListener('pointerup', onPinPointerUp)
  }

  function onPinPointerMove (event: PointerEvent) {
    const pos = percentFromPointer(event)
    if (pos) dragPosition.value = pos
  }

  function onPinPointerUp (event: PointerEvent) {
    window.removeEventListener('pointermove', onPinPointerMove)
    window.removeEventListener('pointerup', onPinPointerUp)

    const pinId = draggingPinId.value
    const finalPosition = dragPosition.value
    draggingPinId.value = undefined
    dragPosition.value = undefined
    if (!pinId || !finalPosition) return

    const distance = Math.hypot(event.clientX - downX, event.clientY - downY)
    if (distance < CLICK_THRESHOLD_PX) {
      emit('pin-click', pinId)
    } else {
      emit('pin-move', pinId, finalPosition.x, finalPosition.y)
    }
  }

  function fitToViewport () {
    if (!viewportRef.value || !imageRef.value) return
    hoveredPinId.value = undefined

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

  function onCanvasClick (event: PointerEvent) {
    if (!props.editable) return
    const target = event.target as HTMLElement
    if (target.closest('.map-controls') || target.closest('.map-marker')) return

    const pos = percentFromPointer(event)
    if (pos) emit('canvas-click', pos.x, pos.y)
  }

  function onPointerUp (event: PointerEvent) {
    panning.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)

    const distance = Math.hypot(event.clientX - downX, event.clientY - downY)
    if (distance < CLICK_THRESHOLD_PX) onCanvasClick(event)
  }

  function onPointerDown (event: PointerEvent) {
    panning.value = true
    downX = event.clientX
    downY = event.clientY
    lastX = event.clientX
    lastY = event.clientY
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  function zoomBy (factor: number, originX: number, originY: number) {
    hoveredPinId.value = undefined
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
    window.removeEventListener('pointermove', onPinPointerMove)
    window.removeEventListener('pointerup', onPinPointerUp)
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

.map-viewport.is-editable {
  cursor: crosshair;
}

.map-viewport.is-editable.is-panning {
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

/* A marker sits on an arbitrary user-uploaded image - outline + shadow keep it legible regardless
   of the map's own colors, rather than relying on contrast with the art underneath. */
.map-marker .v-icon {
  -webkit-text-stroke: 1.5px white;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.5));
}

.map-viewport.is-editable .map-marker {
  cursor: grab;
}

.map-marker--orphan {
  opacity: 0.45;
  filter: grayscale(1);
}

.map-marker--inert {
  pointer-events: none;
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
