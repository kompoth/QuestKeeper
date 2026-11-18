<template>
  <NavBar :app-title="appTitle" back-to="/w" :items="navItems" @logout="handleLogout" />

  <v-main scrollable>
    <router-view :key="route.fullPath" />
  </v-main>

  <v-dialog v-model="renameDialogOpen" width="400">
    <v-card title="Rename">
      <v-card-text>
        <v-text-field v-model="renameDialogTitle" autofocus variant="outlined" @keyup.enter="confirmRename" />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancelRename">Cancel</v-btn>
        <v-btn color="primary" @click="confirmRename">Rename</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
  import type { NavItem } from '@/types/nav-item'
  import type { World } from '@/types/world'
  import { computed, provide, ref, watchEffect } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { createEntity, deleteEntity, getEntity, listEntities, renameEntity } from '@/api/entities'
  import { getWorld } from '@/api/worlds'
  import NavBar from '@/components/NavBar.vue'
  import { useAuth } from '@/composables/useAuth'
  import { useRenameDialog } from '@/composables/useRenameDialog'
  import { refreshNavItemsKey, toNavItem } from '@/utils/nav'

  const { renameDialogOpen, renameDialogTitle, openRenameDialog, confirmRename, cancelRename } = useRenameDialog()
  const { logout } = useAuth()

  const route = useRoute()
  const router = useRouter()

  const worldId = computed(() => route.params.worldId as string)

  const world = ref<World>()
  watchEffect(async () => {
    world.value = await getWorld(worldId.value)
  })
  const appTitle = computed(() => world.value?.name ?? 'Questkeeper')

  const navItems = ref<NavItem[]>([])

  let navItemsRequestId = 0

  async function refreshNavItems () {
    const requestId = ++navItemsRequestId
    const entities = await listEntities(worldId.value)
    if (requestId !== navItemsRequestId) return // a newer refresh already started, discard this stale result

    const entitiesById = new Map(entities.map(entity => [entity.id, entity]))
    const handlers = { onRename: handleRename, onAddPage: handleAddPage, onDelete: handleDelete }
    navItems.value = [
      ...entities
        .filter(entity => entity.parent === null)
        .map(entity => toNavItem(worldId.value, entity, entitiesById, handlers)),
      { id: 'add-page', title: 'Add page', icon: 'mdi-plus', onClick: () => handleAddPage() },
    ]
  }

  watchEffect(refreshNavItems)

  provide(refreshNavItemsKey, refreshNavItems)

  async function handleAddPage (parentId?: string) {
    const created = await createEntity(worldId.value, 'New page', parentId)
    await refreshNavItems()
    router.push(`/w/${worldId.value}/e/${created.id}`)
  }

  async function handleRename (entityId: string) {
    const entity = await getEntity(worldId.value, entityId)
    const title = await openRenameDialog(entity?.name ?? '')
    if (title === undefined) return
    await renameEntity(worldId.value, entityId, title)
    await refreshNavItems()
  }

  async function handleDelete (entityId: string) {
    await deleteEntity(worldId.value, entityId)
    await refreshNavItems()
  }

  async function handleLogout () {
    await logout()
    router.push('/login')
  }
</script>
