<template>
  <div>
    <div class="text-subtitle-2 text-medium-emphasis mb-2">Media</div>

    <p v-if="!loading && items.length === 0" class="text-body-2 text-medium-emphasis">
      No media uploaded yet.
    </p>

    <div v-else class="d-flex flex-wrap ga-2">
      <v-card v-for="item in items" :key="item.fileId" width="96">
        <v-img aspect-ratio="1" cover height="96" :src="apiUrl(item.path)" />

        <v-btn
          aria-label="Delete forever"
          class="position-absolute"
          color="error"
          icon="mdi-close"
          size="x-small"
          style="top: 2px; right: 2px;"
          variant="flat"
          @click="handleDelete(item)"
        />
      </v-card>
    </div>

    <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
  </div>
</template>

<script lang="ts" setup>
  import type { MediaItem } from '@/api/media'
  import { onMounted, ref, watch } from 'vue'
  import { apiUrl } from '@/api/client'
  import { deleteMedia, listMedia } from '@/api/media'
  import { useSnackbar } from '@/composables/useSnackbar'

  const props = defineProps<{
    worldId: string
    entityId: string
  }>()

  const items = ref<MediaItem[]>([])
  const loading = ref(false)

  const { snackbar, snackbarText, snackbarColor, notify } = useSnackbar()

  async function refresh () {
    loading.value = true
    try {
      items.value = await listMedia(props.worldId, props.entityId)
    } finally {
      loading.value = false
    }
  }

  onMounted(refresh)
  watch(() => props.entityId, refresh)

  async function handleDelete (item: MediaItem) {
    try {
      await deleteMedia(props.worldId, props.entityId, item.fileId)
      items.value = items.value.filter(candidate => candidate.fileId !== item.fileId)
    } catch {
      notify('Failed to delete file', 'error')
    }
  }
</script>
