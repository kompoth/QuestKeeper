<template>
  <NavBar :app-title="appTitle" show-back-button @logout="handleLogout">
    <template #sidebar>
      <SidebarTabs :tabs="sidebarTabs">
        <template #entities>
          <EntityNav :items="navItems" />
        </template>

        <template #trash>
          <EntityNav v-if="trashNavItems.length > 0" :items="trashNavItems" />
          <p v-else class="text-body-2 text-medium-emphasis pa-4">Trash is empty.</p>
        </template>

        <template #media />

        <template v-if="isOwner" #settings>
          <v-list density="compact" nav>
            <v-list-item prepend-icon="mdi-tune" title="General" :to="`/w/${worldId}/settings/general`" />
            <v-list-item prepend-icon="mdi-account-group" title="Members" :to="`/w/${worldId}/settings/members`" />
            <v-list-item prepend-icon="mdi-alert-outline" title="Advanced" :to="`/w/${worldId}/settings/advanced`" />
          </v-list>
        </template>
      </SidebarTabs>
    </template>
  </NavBar>

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

  <v-dialog v-model="permissionsDialogOpen" width="560">
    <v-card title="Permissions">
      <v-card-text>
        <v-alert
          v-if="permissionsError"
          class="mb-4"
          closable
          type="error"
          @click:close="permissionsError = undefined"
        >{{ permissionsError }}</v-alert>

        <div class="text-subtitle-2 mb-2">Direct</div>

        <v-list v-if="permissions.direct.length > 0" class="mb-4" density="compact">
          <InviteeItem v-for="grant in permissions.direct" :key="grant.userId" :invite="grantInvite(grant)">
            <template #append>
              <v-chip class="mr-2" size="small">{{ levelLabel(grant.level) }}</v-chip>

              <v-btn
                aria-label="Revoke"
                icon="mdi-close"
                size="small"
                variant="text"
                @click="handleRevoke(grant)"
              />
            </template>
          </InviteeItem>
        </v-list>

        <p v-else class="text-body-2 text-medium-emphasis mb-4">No direct grants.</p>

        <template v-if="permissions.inherited.length > 0">
          <div class="text-subtitle-2 mb-2">Inherited</div>

          <v-list class="mb-4" density="compact">
            <InviteeItem
              v-for="grant in permissions.inherited"
              :key="grant.userId"
              :invite="grantInvite(grant)"
              :subtitle="`From ${ancestorName(grant.fromEntityId)}`"
            >
              <template #append>
                <v-chip size="small">{{ levelLabel(grant.level) }}</v-chip>
              </template>
            </InviteeItem>
          </v-list>
        </template>

        <v-divider class="mb-4" />

        <div class="text-subtitle-2 mb-2">Grant access</div>

        <div class="d-flex ga-2">
          <v-combobox
            v-model="grantSelection"
            density="compact"
            item-title="title"
            item-value="value"
            :items="memberOptions"
            label="Grantee"
            variant="outlined"
          >
            <template #item="{ item, props: itemProps }">
              <InviteeItem v-bind="itemProps" :invite="item.invite" />
            </template>
          </v-combobox>

          <v-select
            v-model="grantLevel"
            density="compact"
            :items="LEVEL_OPTIONS"
            label="Level"
            style="max-width: 160px;"
            variant="outlined"
          />
        </div>

        <v-btn
          block
          color="primary"
          :disabled="!canGrant"
          :loading="granting"
          variant="flat"
          @click="handleGrant"
        >
          Grant
        </v-btn>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="permissionsDialogOpen = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="purgeConfirmOpen" width="400">
    <v-card title="Delete forever">
      <v-card-text>This cannot be undone.</v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="purgeConfirmOpen = false">Cancel</v-btn>
        <v-btn color="red" variant="flat" @click="confirmPurge">Delete forever</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
  import type { SidebarTab } from '@/components/SidebarTabs.vue'
  import type { Entity } from '@/types/entity'
  import type { InviteSummary } from '@/types/invite'
  import type { NavItem } from '@/types/nav-item'
  import type { EntityGrant, EntityPermissions, PermissionLevel } from '@/types/permission'
  import type { World } from '@/types/world'
  import { computed, provide, ref, watchEffect } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { ApiError } from '@/api/client'
  import {
    createEntity,
    deleteEntity,
    getEntity,
    listEntities,
    listTrash,
    purgeEntity,
    renameEntity,
    restoreEntity,
    restoreEntityBranch,
  } from '@/api/entities'
  import { acceptInvite, listInvites, listMyPendingInvites } from '@/api/invites'
  import { getEntityPermissions, grantPermission, revokePermission } from '@/api/permissions'
  import { getWorld } from '@/api/worlds'
  import EntityNav from '@/components/EntityNav.vue'
  import InviteeItem from '@/components/InviteeItem.vue'
  import NavBar from '@/components/NavBar.vue'
  import SidebarTabs from '@/components/SidebarTabs.vue'
  import { useAuth } from '@/composables/useAuth'
  import { useRenameDialog } from '@/composables/useRenameDialog'
  import { anonymousName } from '@/utils/anonymousName'
  import {
    entityTrashVersionKey,
    isEntityOrDescendant,
    isWorldOwnerKey,
    refreshNavItemsKey,
    toNavItem,
    toTrashNavItem,
  } from '@/utils/nav'

  const LEVEL_OPTIONS: { title: string, value: PermissionLevel }[] = [
    { title: 'Can read', value: 'read' },
    { title: 'Can edit', value: 'write' },
  ]

  const { renameDialogOpen, renameDialogTitle, openRenameDialog, confirmRename, cancelRename } = useRenameDialog()
  const { currentUser, logout } = useAuth()

  const route = useRoute()
  const router = useRouter()

  const worldId = computed(() => route.params.worldId as string)

  const world = ref<World>()
  watchEffect(async () => {
    world.value = await getWorld(worldId.value)
  })

  // Opening a world auto-accepts a still-pending invite to it.
  watchEffect(async () => {
    const openedWorldId = worldId.value
    const pendingInvites = await listMyPendingInvites()
    if (pendingInvites.some(invite => invite.worldId === openedWorldId)) {
      await acceptInvite(openedWorldId)
    }
  })
  const appTitle = computed(() => world.value?.name ?? 'Questkeeper')
  const isOwner = computed(() => world.value !== undefined && world.value.ownerId === currentUser.value?.id)
  provide(isWorldOwnerKey, isOwner)

  const sidebarTabs = computed<SidebarTab[]>(() => [
    { value: 'entities', icon: 'mdi-file-tree', label: 'Entities' },
    { value: 'trash', icon: 'mdi-delete-restore', label: 'Trash' },
    { value: 'media', icon: 'mdi-image-multiple', label: 'Media', disabled: true },
    ...isOwner.value ? [{ value: 'settings', icon: 'mdi-cog', label: 'Settings' }] : [],
  ])

  const navItems = ref<NavItem[]>([])

  let navItemsRequestId = 0
  let entitiesById = new Map<string, Entity>()

  async function refreshNavItems () {
    const requestId = ++navItemsRequestId
    const canAddRootPage = isOwner.value // read before the await so watchEffect tracks it
    const entities = await listEntities(worldId.value)
    if (requestId !== navItemsRequestId) return // a newer refresh already started, discard this stale result

    entitiesById = new Map(entities.map(entity => [entity.id, entity]))
    const handlers = {
      onRename: handleRename, onAddPage: handleAddPage, onDelete: handleDelete, onPermissions: openPermissionsDialog,
    }
    navItems.value = [
      ...entities
        .filter(entity => entity.parent === null)
        .map(entity => toNavItem(worldId.value, entity, entitiesById, handlers, isOwner.value)),
      ...canAddRootPage
        ? [{ id: 'add-page', title: 'Add page', icon: 'mdi-note-plus-outline', onClick: () => handleAddPage() }]
        : [],
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

  // Bumped after every trash/restore/purge, so a currently open entity page (which doesn't otherwise
  // react to a change made from the sidebar) knows to re-fetch itself.
  const entityTrashVersion = ref(0)
  provide(entityTrashVersionKey, entityTrashVersion)

  async function handleDelete (entityId: string) {
    const shouldRedirect = openEntityIsOrIsDescendantOf(entitiesById, entityId)

    await deleteEntity(worldId.value, entityId)
    await Promise.all([refreshNavItems(), refreshTrash()])
    entityTrashVersion.value++

    if (shouldRedirect) {
      router.push(`/w/${worldId.value}`)
    }
  }

  async function handleLogout () {
    await logout()
    router.push('/login')
  }

  function openEntityIsOrIsDescendantOf (idsById: Map<string, Entity>, targetId: string): boolean {
    const openEntityId = route.params.entityId as string | undefined
    return openEntityId !== undefined && isEntityOrDescendant(idsById, targetId, openEntityId)
  }

  const trashNavItems = ref<NavItem[]>([])

  let trashRequestId = 0
  let trashEntitiesById = new Map<string, Entity>()

  async function refreshTrash () {
    const requestId = ++trashRequestId
    const entities = await listTrash(worldId.value)
    if (requestId !== trashRequestId) return // a newer refresh already started, discard this stale result

    trashEntitiesById = new Map(entities.map(entity => [entity.id, entity]))
    const handlers = { onRestore: handleRestore, onRestoreBranch: handleRestoreBranch, onPurge: requestPurge }
    trashNavItems.value = entities
      .filter(entity => entity.parent === null || !trashEntitiesById.has(entity.parent))
      .map(entity => toTrashNavItem(worldId.value, entity, trashEntitiesById, handlers))
  }

  watchEffect(refreshTrash)

  async function handleRestore (entityId: string) {
    await restoreEntity(worldId.value, entityId)
    await Promise.all([refreshNavItems(), refreshTrash()])
    entityTrashVersion.value++
  }

  async function handleRestoreBranch (entityId: string) {
    await restoreEntityBranch(worldId.value, entityId)
    await Promise.all([refreshNavItems(), refreshTrash()])
    entityTrashVersion.value++
  }

  const purgeConfirmEntityId = ref<string>()
  const purgeConfirmOpen = ref(false)

  function requestPurge (entityId: string) {
    purgeConfirmEntityId.value = entityId
    purgeConfirmOpen.value = true
  }

  async function confirmPurge () {
    if (!purgeConfirmEntityId.value) return
    const entityId = purgeConfirmEntityId.value
    const shouldRedirect = openEntityIsOrIsDescendantOf(trashEntitiesById, entityId)

    await purgeEntity(worldId.value, entityId)
    purgeConfirmOpen.value = false
    await Promise.all([refreshNavItems(), refreshTrash()])
    entityTrashVersion.value++

    if (shouldRedirect) {
      router.push(`/w/${worldId.value}`)
    }
  }

  const permissionsEntityId = ref<string>()
  const permissionsDialogOpen = ref(false)
  const permissions = ref<EntityPermissions>({ direct: [], inherited: [] })
  const permissionsError = ref<string>()

  interface GrantOption {
    title: string
    value: string
    invite: InviteSummary
  }

  // v-combobox always returns the full item object on selection (never just item-value) -
  // https://vuetifyjs.com/en/components/combobox/#caveats - so grantEmail normalizes it to a string.
  const grantSelection = ref<string | GrantOption>('')
  const grantEmail = computed(() => (
    typeof grantSelection.value === 'string' ? grantSelection.value : grantSelection.value.value
  ))
  const grantLevel = ref<PermissionLevel>()
  const granting = ref(false)

  const invites = ref<InviteSummary[]>([])
  const memberOptions = computed<GrantOption[]>(() => invites.value.map(invite => ({
    title: invite.inviteeName ?? anonymousName(invite.inviteeEmail),
    value: invite.inviteeEmail,
    invite,
  })))

  const canGrant = computed(() => grantEmail.value !== '' && grantLevel.value !== undefined)

  function ancestorName (entityId: string): string {
    return entitiesById.get(entityId)?.name ?? entityId
  }

  function levelLabel (level: PermissionLevel): string {
    return level === 'write' ? 'Can edit' : 'Can read'
  }

  function grantInvite (grant: EntityGrant): InviteSummary {
    // A grant has no "accepted" flag of its own - a hidden name (masked server-side while the
    // grantee's invite to this world is still pending) is the only signal InviteeItem needs.
    return { inviteeEmail: grant.email, inviteeName: grant.name, accepted: grant.name !== null }
  }

  async function refreshPermissions () {
    if (!permissionsEntityId.value) return
    permissions.value = await getEntityPermissions(worldId.value, permissionsEntityId.value)
  }

  async function openPermissionsDialog (entityId: string) {
    permissionsEntityId.value = entityId
    permissionsError.value = undefined
    grantSelection.value = ''
    grantLevel.value = undefined
    permissionsDialogOpen.value = true
    invites.value = await listInvites(worldId.value)
    await refreshPermissions()
  }

  async function handleGrant () {
    if (!permissionsEntityId.value || !canGrant.value || !grantLevel.value) return
    permissionsError.value = undefined
    granting.value = true
    try {
      await grantPermission(worldId.value, permissionsEntityId.value, grantEmail.value, grantLevel.value)
      grantSelection.value = ''
      grantLevel.value = undefined
      await refreshPermissions()
    } catch (error) {
      permissionsError.value = error instanceof ApiError ? error.detail : 'Something went wrong, please try again'
    } finally {
      granting.value = false
    }
  }

  async function handleRevoke (grant: EntityGrant) {
    if (!permissionsEntityId.value) return
    try {
      await revokePermission(worldId.value, grant.userId, permissionsEntityId.value)
      await refreshPermissions()
    } catch (error) {
      permissionsError.value = error instanceof ApiError ? error.detail : 'Something went wrong, please try again'
    }
  }
</script>
