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
    <v-card :title="worldFormIsEdit ? 'Edit World' : 'New World'">
      <v-card-text>
        <v-text-field
          v-model="worldFormName"
          autofocus
          label="Name"
          variant="outlined"
          @keyup.enter="confirmWorldForm"
        />

        <v-textarea v-model="worldFormDescription" label="Description" variant="outlined" />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancelWorldForm">Cancel</v-btn>
        <v-btn color="primary" @click="confirmWorldForm">{{ worldFormIsEdit ? 'Save' : 'Create' }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { useRouter } from 'vue-router'
  import NavBar from '@/components/NavBar.vue'
  import { useWorldFormDialog } from '@/composables/useWorldFormDialog'
  import { createWorld, listWorlds } from '@/data/worlds'

  const worlds = ref(listWorlds())

  const router = useRouter()

  const { worldFormOpen, worldFormName, worldFormDescription, worldFormIsEdit, openWorldFormDialog, confirmWorldForm, cancelWorldForm } = useWorldFormDialog()

  async function handleCreateWorld () {
    const result = await openWorldFormDialog()
    if (result === undefined) return
    createWorld(result.name, result.description)
    worlds.value = listWorlds()
  }

  function handleLogout () {
    router.push('/login')
  }
</script>
