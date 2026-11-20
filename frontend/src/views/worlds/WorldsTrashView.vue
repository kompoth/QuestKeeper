<template>
  <h1 class="text-h4 mb-4">Trash</h1>

  <p v-if="!loading && worlds.length === 0" class="text-body-2 text-medium-emphasis">
    Nothing in the trash.
  </p>

  <v-row v-else>
    <v-col
      v-for="world in worlds"
      :key="world.id"
      cols="12"
      md="4"
      sm="6"
    >
      <WorldCard :world="world">
        <template #overlay>
          <v-chip
            v-if="world.deletedAt"
            class="position-absolute"
            color="error"
            prepend-icon="mdi-delete-clock-outline"
            size="small"
            style="top: 8px; left: 8px;"
            variant="flat"
          >
            {{ formatDate(world.deletedAt) }}
          </v-chip>
        </template>

        <template #actions>
          <v-spacer />

          <v-btn
            color="primary"
            prepend-icon="mdi-restore"
            size="small"
            variant="tonal"
            @click="handleRestore(world)"
          >
            Restore
          </v-btn>

          <v-btn
            color="error"
            prepend-icon="mdi-delete-forever"
            size="small"
            variant="tonal"
            @click="openPurgeDialog(world)"
          >
            Delete forever
          </v-btn>
        </template>
      </WorldCard>
    </v-col>
  </v-row>

  <v-dialog v-model="purgeDialog" max-width="480">
    <v-card v-if="purgeTarget" title="Delete forever">
      <v-card-text>
        <p class="mb-4">
          This permanently deletes "{{ purgeTarget.name }}", every one of its pages, and their uploaded media.
          Type its name below to confirm - this cannot be undone.
        </p>

        <v-text-field v-model="purgeConfirmation" label="World name" variant="outlined" />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="purgeDialog = false">Cancel</v-btn>

        <v-btn
          color="error"
          :disabled="purgeConfirmation !== purgeTarget.name"
          prepend-icon="mdi-delete-forever"
          variant="flat"
          @click="handlePurge"
        >
          Delete forever
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
</template>

<script lang="ts" setup>
  import type { World } from '@/types/world'
  import { onMounted, ref } from 'vue'
  import { listWorldTrash, purgeWorld, restoreWorld } from '@/api/worlds'
  import WorldCard from '@/components/WorldCard.vue'
  import { formatDate } from '@/utils/date'

  const worlds = ref<World[]>([])
  const loading = ref(false)

  const purgeDialog = ref(false)
  const purgeTarget = ref<World>()
  const purgeConfirmation = ref('')

  const snackbar = ref(false)
  const snackbarText = ref('')
  const snackbarColor = ref('success')

  function notify (text: string, color: string) {
    snackbarText.value = text
    snackbarColor.value = color
    snackbar.value = true
  }

  async function refreshTrash () {
    loading.value = true
    try {
      worlds.value = await listWorldTrash()
    } finally {
      loading.value = false
    }
  }

  onMounted(refreshTrash)

  async function handleRestore (world: World) {
    try {
      await restoreWorld(world.id)
      await refreshTrash()
      notify(`${world.name} restored`, 'success')
    } catch {
      notify('Failed to restore world', 'error')
    }
  }

  function openPurgeDialog (world: World) {
    purgeTarget.value = world
    purgeConfirmation.value = ''
    purgeDialog.value = true
  }

  async function handlePurge () {
    if (!purgeTarget.value || purgeConfirmation.value !== purgeTarget.value.name) return
    const world = purgeTarget.value
    try {
      await purgeWorld(world.id)
      purgeDialog.value = false
      await refreshTrash()
      notify(`${world.name} deleted forever`, 'success')
    } catch {
      notify('Failed to delete world', 'error')
    }
  }
</script>
