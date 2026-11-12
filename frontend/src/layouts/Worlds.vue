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

        <!-- TODO: world creation -->
        <v-col cols="12" md="4" sm="6">
          <v-card height="220" hover>
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
</template>

<script lang="ts" setup>
  import { useRouter } from 'vue-router'
  import NavBar from '@/components/NavBar.vue'
  import { listWorlds } from '@/data/worlds'

  const worlds = listWorlds()

  const router = useRouter()

  function handleLogout () {
    router.push('/login')
  }
</script>
