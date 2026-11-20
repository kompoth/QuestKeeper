<template>
  <v-container>
    <h1 class="text-h5 mb-4">Advanced</h1>

    <div class="text-subtitle-1 text-error font-weight-bold mb-2">Danger zone</div>

    <p class="text-body-2 mb-4">
      Deleting <strong>{{ world?.name }}</strong> is irreversible. Type its name below to confirm.
    </p>

    <v-text-field v-model="deleteConfirmation" label="World name" variant="outlined" />

    <v-btn
      color="error"
      :disabled="!canDelete"
      variant="flat"
      @click="handleDelete"
    >
      Delete this world
    </v-btn>
  </v-container>
</template>

<script lang="ts" setup>
  import type { World } from '@/types/world'
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { deleteWorld, getWorld } from '@/api/worlds'

  const route = useRoute()
  const router = useRouter()
  const worldId = route.params.worldId as string

  const world = ref<World>()
  const deleteConfirmation = ref('')

  const canDelete = computed(() => deleteConfirmation.value !== '' && deleteConfirmation.value === world.value?.name)

  onMounted(async () => {
    world.value = await getWorld(worldId)
  })

  async function handleDelete () {
    if (!canDelete.value) return
    await deleteWorld(worldId)
    router.push('/w')
  }
</script>
