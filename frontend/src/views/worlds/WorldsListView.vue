<template>
  <h1 class="text-h4 mb-4">Worlds</h1>

  <v-row>
    <v-col
      v-for="world in sortedWorlds"
      :key="world.id"
      cols="12"
      md="4"
      sm="6"
    >
      <v-card height="220" hover :to="`/w/${world.id}`">
        <v-sheet class="d-flex align-center justify-center" color="surface-variant" height="140">
          <v-icon color="on-surface-variant" icon="mdi-image" size="48" />

          <v-chip
            class="position-absolute"
            :color="isOwner(world) ? 'primary' : 'secondary'"
            size="small"
            style="top: 8px; left: 8px;"
            variant="flat"
          >
            {{ world.ownerName }}
          </v-chip>

          <v-chip
            v-if="hasPendingInvite(world)"
            class="position-absolute"
            color="amber"
            prepend-icon="mdi-alert-decagram-outline"
            size="small"
            style="top: 8px; right: 8px;"
            variant="flat"
          >
            New
          </v-chip>
        </v-sheet>

        <v-card-title>{{ world.name }}</v-card-title>
        <v-card-subtitle>{{ world.description }}</v-card-subtitle>
      </v-card>
    </v-col>

    <v-col cols="12" md="4" sm="6">
      <v-card
        class="d-flex flex-column align-center justify-center text-center"
        height="220"
        hover
        variant="outlined"
        @click="handleCreateWorld"
      >
        <v-icon color="on-surface-variant" icon="mdi-plus" size="48" />
        <v-card-title>New World</v-card-title>
        <v-card-subtitle>Tell me a tale, great or small</v-card-subtitle>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts" setup>
  import type { World } from '@/types/world'
  import { computed, onMounted, ref } from 'vue'
  import { listMyPendingInvites } from '@/api/invites'
  import { createWorld, listWorlds } from '@/api/worlds'
  import { useAuth } from '@/composables/useAuth'

  const { currentUser } = useAuth()

  const worlds = ref<World[]>([])
  const pendingInviteWorldIds = ref(new Set<string>())

  function isOwner (world: World): boolean {
    return world.ownerId === currentUser.value?.id
  }

  function hasPendingInvite (world: World): boolean {
    return pendingInviteWorldIds.value.has(world.id)
  }

  const sortedWorlds = computed(() => [
    ...worlds.value.filter(world => isOwner(world)),
    ...worlds.value.filter(world => !isOwner(world)),
  ])

  let worldsRequestId = 0

  async function refreshWorlds () {
    const requestId = ++worldsRequestId
    const [result, pendingInvites] = await Promise.all([listWorlds(), listMyPendingInvites()])
    if (requestId !== worldsRequestId) return // a newer refresh already started, discard this stale result
    worlds.value = result
    pendingInviteWorldIds.value = new Set(pendingInvites.map(invite => invite.worldId))
  }

  onMounted(refreshWorlds)

  async function handleCreateWorld () {
    await createWorld('New World', '')
    await refreshWorlds()
  }
</script>
