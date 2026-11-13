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
  import { computed, ref, watchEffect } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import NavBar from '@/components/NavBar.vue'
  import { useRenameDialog } from '@/composables/useRenameDialog'
  import { createEntity, deleteEntity, getEntity, listEntities, renameEntity } from '@/data/entities'
  import { getWorld } from '@/data/worlds'
  import { toNavItem } from '@/utils/nav'

  const { renameDialogOpen, renameDialogTitle, openRenameDialog, confirmRename, cancelRename } = useRenameDialog()

  const route = useRoute()
  const router = useRouter()

  const worldId = computed(() => route.params.worldId as string)

  const appTitle = computed(() => getWorld(worldId.value)?.name ?? 'Questkeeper')

  const navItems = ref<NavItem[]>([])

  async function refreshNavItems () {
    const entities = await listEntities(worldId.value)
    const handlers = { onRename: handleRename, onAddPage: handleAddPage, onDelete: handleDelete }
    navItems.value = [
      ...await Promise.all(entities.map(entity => toNavItem(worldId.value, entity, handlers))),
      { id: 'add-page', title: 'Add page', icon: 'mdi-plus', onClick: () => handleAddPage() },
    ]
  }

  watchEffect(refreshNavItems)

  async function handleAddPage (parentId?: string) {
    const created = await createEntity(worldId.value, parentId, 'New page')
    await refreshNavItems()
    router.push(`/w/${worldId.value}/e/${created.id}`)
  }

  async function handleRename (entityId: string) {
    const entity = await getEntity(entityId)
    const title = await openRenameDialog(entity?.title ?? '')
    if (title === undefined) return
    await renameEntity(entityId, title)
    await refreshNavItems()
  }

  async function handleDelete (entityId: string) {
    await deleteEntity(entityId)
    await refreshNavItems()
  }

  function handleLogout () {
    router.push('/login')
  }
</script>
