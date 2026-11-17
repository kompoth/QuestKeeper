<template>
  <NavBar app-title="Questkeeper" @logout="handleLogout" />

  <v-main>
    <v-container>
      <h1 class="text-h4 mb-4">Worlds</h1>

      <v-row>
        <v-col
          v-for="world in worlds"
          :key="world.id"
          cols="12"
          md="4"
          sm="6"
        >
          <v-card height="220" hover :to="`/w/${world.id}`">
            <v-sheet class="d-flex align-center justify-center" color="surface-variant" height="140">
              <v-icon color="on-surface-variant" icon="mdi-image" size="48" />
            </v-sheet>

            <v-btn
              aria-label="World settings"
              class="position-absolute"
              color="surface"
              icon="mdi-cog"
              size="small"
              style="top: 8px; right: 8px;"
              variant="elevated"
              @click.stop.prevent="handleSettings(world)"
            />

            <v-card-title>{{ world.name }}</v-card-title>
            <v-card-subtitle>{{ world.description }}</v-card-subtitle>
          </v-card>
        </v-col>

        <v-col cols="12" md="4" sm="6">
          <v-card height="220" hover @click="handleCreateWorld">
            <v-sheet class="d-flex align-center justify-center" color="surface-variant" height="140">
              <v-icon color="on-surface-variant" icon="mdi-image" size="48" />
            </v-sheet>

            <v-card-title>
              <v-icon icon="mdi-plus" start />
              New World
            </v-card-title>

            <v-card-subtitle>Tell me a tale, great or small</v-card-subtitle>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-main>

  <v-dialog v-model="worldFormOpen" width="400">
    <v-card title="World settings">
      <v-card-text>
        <v-text-field
          v-model="worldFormName"
          autofocus
          label="Name"
          variant="outlined"
          @keyup.enter="confirmWorldForm"
        />

        <v-textarea v-model="worldFormDescription" label="Description" variant="outlined" />

        <v-divider class="my-4" />

        <div class="text-subtitle-1 text-error font-weight-bold mb-2">Danger zone</div>

        <p class="text-body-2 mb-4">
          Deleting <strong>{{ settingsWorld?.name }}</strong> is irreversible. Type its name below to confirm.
        </p>

        <v-text-field v-model="deleteConfirmation" label="World name" variant="outlined" />

        <v-btn
          block
          color="error"
          :disabled="!canDeleteWorld"
          variant="flat"
          @click="handleDeleteWorld"
        >
          Delete this world
        </v-btn>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancelWorldForm">Cancel</v-btn>
        <v-btn color="primary" @click="confirmWorldForm">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
  import type { World } from '@/types/world'
  import { computed, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import NavBar from '@/components/NavBar.vue'
  import { useWorldFormDialog } from '@/composables/useWorldFormDialog'
  import { createWorld, deleteWorld, listWorlds, updateWorld } from '@/data/worlds'

  const worlds = ref(listWorlds())

  const router = useRouter()

  const { worldFormOpen, worldFormName, worldFormDescription, openWorldFormDialog, confirmWorldForm, cancelWorldForm } = useWorldFormDialog()

  const settingsWorld = ref<World>()
  const deleteConfirmation = ref('')

  const canDeleteWorld = computed(() => deleteConfirmation.value !== '' && deleteConfirmation.value === settingsWorld.value?.name)

  function handleCreateWorld () {
    createWorld('New World', '')
    worlds.value = listWorlds()
  }

  async function handleSettings (world: World) {
    settingsWorld.value = world
    deleteConfirmation.value = ''
    const result = await openWorldFormDialog(world)
    if (result === undefined) return
    updateWorld(world.id, result.name, result.description)
    worlds.value = listWorlds()
  }

  function handleDeleteWorld () {
    if (!settingsWorld.value || !canDeleteWorld.value) return
    deleteWorld(settingsWorld.value.id)
    worlds.value = listWorlds()
    cancelWorldForm()
  }

  function handleLogout () {
    router.push('/login')
  }
</script>
