<template>
  <v-container fluid>
    <h1 class="text-h5 mb-4">General</h1>

    <v-alert
      v-if="saved"
      class="mb-4"
      closable
      type="success"
      @click:close="saved = false"
    >Saved</v-alert>

    <v-text-field v-model="name" label="Name" variant="outlined" />
    <v-textarea v-model="description" label="Description" variant="outlined" />

    <v-btn color="primary" :loading="saving" variant="flat" @click="handleSave">Save</v-btn>
  </v-container>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getWorld, updateWorld } from '@/api/worlds'

  const route = useRoute()
  const worldId = route.params.worldId as string

  const name = ref('')
  const description = ref('')
  const saving = ref(false)
  const saved = ref(false)

  onMounted(async () => {
    const world = await getWorld(worldId)
    name.value = world?.name ?? ''
    description.value = world?.description ?? ''
  })

  async function handleSave () {
    saving.value = true
    saved.value = false
    try {
      await updateWorld(worldId, name.value, description.value)
      saved.value = true
    } finally {
      saving.value = false
    }
  }
</script>
