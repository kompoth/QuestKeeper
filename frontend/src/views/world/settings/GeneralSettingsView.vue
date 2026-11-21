<template>
  <v-container>
    <h1 class="text-h5 mb-4">General</h1>

    <v-alert
      v-if="saved"
      class="mb-4"
      closable
      type="success"
      @click:close="saved = false"
    >Saved</v-alert>

    <v-row class="mb-4">
      <v-col cols="12" md="4" sm="6">
        <v-img
          v-if="pic"
          class="mb-2"
          cover
          height="140"
          :src="apiUrl(pic)"
        />

        <v-sheet v-else class="d-flex align-center justify-center mb-2" color="surface-variant" height="140">
          <v-icon color="on-surface-variant" icon="mdi-image" size="48" />
        </v-sheet>

        <v-btn
          block
          :loading="uploadingPic"
          prepend-icon="mdi-upload"
          variant="tonal"
          @click="fileInput?.click()"
        >
          Change picture
        </v-btn>
      </v-col>
    </v-row>

    <input
      ref="fileInput"
      accept="image/png,image/jpeg,image/webp,image/gif"
      hidden
      type="file"
      @change="handlePicSelected"
    >

    <v-text-field v-model="name" label="Name" variant="outlined" />
    <v-textarea v-model="description" label="Description" variant="outlined" />

    <v-btn color="primary" :loading="saving" variant="flat" @click="handleSave">Save</v-btn>

    <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
  </v-container>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { apiUrl } from '@/api/client'
  import { getWorld, updateWorld, uploadWorldPic } from '@/api/worlds'
  import { useSnackbar } from '@/composables/useSnackbar'

  const route = useRoute()
  const worldId = route.params.worldId as string

  const name = ref('')
  const description = ref('')
  const pic = ref<string | null>(null)
  const saving = ref(false)
  const saved = ref(false)
  const uploadingPic = ref(false)
  const fileInput = ref<HTMLInputElement>()

  const { snackbar, snackbarText, snackbarColor, notify } = useSnackbar()

  onMounted(async () => {
    const world = await getWorld(worldId)
    name.value = world?.name ?? ''
    description.value = world?.description ?? ''
    pic.value = world?.pic ?? null
  })

  async function handleSave () {
    saving.value = true
    saved.value = false
    try {
      await updateWorld(worldId, name.value, description.value, pic.value)
      saved.value = true
    } finally {
      saving.value = false
    }
  }

  async function handlePicSelected (event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) {
      return
    }
    uploadingPic.value = true
    try {
      const newPic = await uploadWorldPic(worldId, file)
      await updateWorld(worldId, name.value, description.value, newPic)
      pic.value = newPic
    } catch {
      notify('Failed to update picture', 'error')
    } finally {
      uploadingPic.value = false
      ;(event.target as HTMLInputElement).value = ''
    }
  }
</script>
