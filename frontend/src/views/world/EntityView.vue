<template>
  <v-container class="pa-0 ma-0 fill-height d-flex flex-column" fluid>
    <template v-if="entity">
      <v-toolbar color="background" density="compact">
        <v-toolbar-title>
          <v-breadcrumbs class="text-body-small" density="compact" :items="breadcrumbItems">
            <template #divider>
              <v-icon icon="mdi-chevron-right" />
            </template>
          </v-breadcrumbs>
        </v-toolbar-title>

        <div class="mr-5 d-flex ga-2">
          <v-chip v-if="entity.deletedAt" color="warning" label prepend-icon="mdi-delete-restore">
            In Trash
          </v-chip>

          <v-chip
            v-else-if="entity.access.write"
            :color="entityEditable ? 'primary' : 'default'"
            label
            @click="entityEditable = !entityEditable"
          >
            <v-icon :icon="entityEditable ? 'mdi-pencil' : 'mdi-text-long'" start />
            {{ entityEditable ? 'Edit mode' : 'Reading mode' }}
          </v-chip>

          <v-btn
            v-if="articleEditable && !entity.map"
            color="primary"
            :disabled="!articleDirty"
            :loading="savingArticle"
            prepend-icon="mdi-content-save"
            variant="flat"
            @click="handleSaveArticle"
          >
            Save
          </v-btn>
        </div>
      </v-toolbar>

      <v-alert
        v-if="actionError"
        class="mx-4 mt-2"
        closable
        type="error"
        @click:close="actionError = undefined"
      >{{ actionError }}</v-alert>

      <div class="entity-content flex-1-1-100 overflow-y-auto">
        <EntityMap
          v-if="entity.map"
          :editable="mapEditable"
          :entity-names="entityNames"
          :map="entity.map"
          :valid-entity-ids="validEntityIds"
          @canvas-click="handleCanvasClick"
          @open="openEntity"
          @pin-click="handlePinClick"
          @pin-move="handlePinMove"
        />

        <template v-else>
          <EntityArticle
            class="pa-4"
            :editable="articleEditable"
            :entity-id="entity.id"
            :model-value="savedMarkdown"
            :world-id="worldId"
            @update:model-value="handleArticleChange"
            @upload-error="actionError = $event"
          />
        </template>
      </div>
    </template>

    <v-dialog v-model="pinMenuOpen" width="360">
      <v-card :title="pinMenuEntityName">
        <v-list density="compact">
          <v-list-item
            :disabled="pinMenuOrphan"
            prepend-icon="mdi-open-in-new"
            title="Open"
            @click="openPinEntity"
          />

          <v-list-item prepend-icon="mdi-swap-horizontal" title="Rebind" @click="startRebindPin" />
          <v-list-item prepend-icon="mdi-delete-outline" title="Delete pin" @click="deletePinFromMenu" />
        </v-list>
      </v-card>
    </v-dialog>

    <v-dialog v-model="pinPickerOpen" width="480">
      <EntityPicker
        :entities="worldEntities"
        :title="pinPickerMode === 'add' ? 'Add pin' : 'Rebind pin'"
        @cancel="pinPickerOpen = false"
        @create="handlePinPickerCreate"
        @select="handlePinPickerSelect"
      />
    </v-dialog>
  </v-container>
</template>

<script lang="ts" setup>
  import type { Entity } from '@/types/entity'
  import { computed, inject, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
  import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
  import {
    addMapPin,
    createEntity,
    deleteMapPin,
    getEntity,
    listEntities,
    listTrash,
    setArticle,
    updateMapPin,
  } from '@/api/entities'
  import EntityArticle from '@/components/EntityArticle.vue'
  import EntityMap from '@/components/EntityMap.vue'
  import EntityPicker from '@/components/EntityPicker.vue'
  import { useConfirmDialog } from '@/composables/useConfirmDialog'
  import { entityTrashVersionKey, refreshNavItemsKey } from '@/utils/nav'

  interface BreadcrumbItem {
    title: string
    to?: string
    disabled?: boolean
  }

  const route = useRoute()
  const router = useRouter()
  const { confirmDialog } = useConfirmDialog()

  const worldId = computed(() => route.params.worldId as string)

  const entityEditable = ref(false)
  const entityTrashVersion = inject(entityTrashVersionKey)
  const refreshNavItems = inject(refreshNavItemsKey)

  const entity = ref<Entity>()
  const entityPath = ref<Entity[]>([])
  const actionError = ref<string>()
  const articleEditable = computed(() => entityEditable.value && !entity.value?.deletedAt)
  const mapEditable = computed(() => entityEditable.value && !entity.value?.deletedAt)

  const savedMarkdown = ref('')
  const draftMarkdown = ref('')
  const savingArticle = ref(false)
  const articleDirty = computed(() => draftMarkdown.value !== savedMarkdown.value)

  const breadcrumbItems = computed(() => {
    const items: BreadcrumbItem[] = []

    for (const [index, pathEntity] of entityPath.value.entries()) {
      items.push(
        index === entityPath.value.length - 1
          ? { title: pathEntity.name, disabled: true }
          : { title: pathEntity.name, to: `/w/${worldId.value}/e/${pathEntity.id}` },
      )
    }

    return items
  })

  async function getEntityPath (leaf: Entity): Promise<Entity[]> {
    const path = [leaf]
    let current = leaf
    while (current.parent) {
      const parent = await getEntity(worldId.value, current.parent)
      if (!parent) break
      path.unshift(parent)
      current = parent
    }
    return path
  }

  // Alive entities the pin picker can search, and every entity (alive or trashed) the map's pins
  // might reference - a trashed-but-not-purged entity still resolves (see `get_entity`), so only a
  // purged one counts as a truly orphaned pin target.
  const worldEntities = ref<Entity[]>([])
  const validEntityIds = ref<Set<string>>(new Set())
  const entityNames = ref<Map<string, string>>(new Map())

  async function refreshWorldEntities () {
    const [alive, trashed] = await Promise.all([listEntities(worldId.value), listTrash(worldId.value)])
    worldEntities.value = alive
    const everyEntity = [...alive, ...trashed]
    validEntityIds.value = new Set(everyEntity.map(e => e.id))
    entityNames.value = new Map(everyEntity.map(e => [e.id, e.name]))
  }

  async function refreshEntity () {
    const fetchedEntity = await getEntity(worldId.value, route.params.entityId as string)
    // Set together, synchronously, so EntityArticle never mounts with a stale/empty model-value
    // between `entity` updating and `savedMarkdown` catching up (no `await` in between).
    entity.value = fetchedEntity
    savedMarkdown.value = fetchedEntity?.article?.markdown ?? ''
    draftMarkdown.value = savedMarkdown.value

    entityPath.value = fetchedEntity ? await getEntityPath(fetchedEntity) : []
    if (fetchedEntity?.map) await refreshWorldEntities()
  }

  watchEffect(() => {
    void entityTrashVersion?.value // read so a trash/restore/purge elsewhere also triggers a re-fetch here
    refreshEntity()
  })

  function openEntity (entityId: string) {
    router.push(`/w/${worldId.value}/e/${entityId}`)
  }

  const pinMenuOpen = ref(false)
  const pinMenuPinId = ref<string>()
  const pinPickerOpen = ref(false)
  const pinPickerMode = ref<'add' | 'rebind'>('add')
  const pendingPinCoords = ref<{ x: number, y: number }>()

  const pinMenuEntityName = computed(() => {
    const pin = entity.value?.map?.pins.find(p => p.id === pinMenuPinId.value)
    if (!pin) return ''
    return entityNames.value.get(pin.entityId) ?? 'Unknown entity (deleted)'
  })

  const pinMenuOrphan = computed(() => {
    const pin = entity.value?.map?.pins.find(p => p.id === pinMenuPinId.value)
    return pin ? !validEntityIds.value.has(pin.entityId) : false
  })

  function handleCanvasClick (x: number, y: number) {
    pendingPinCoords.value = { x, y }
    pinPickerMode.value = 'add'
    pinPickerOpen.value = true
  }

  function handlePinClick (pinId: string) {
    pinMenuPinId.value = pinId
    pinMenuOpen.value = true
  }

  function openPinEntity () {
    const pin = entity.value?.map?.pins.find(p => p.id === pinMenuPinId.value)
    pinMenuOpen.value = false
    if (pin) openEntity(pin.entityId)
  }

  function startRebindPin () {
    pinMenuOpen.value = false
    pinPickerMode.value = 'rebind'
    pinPickerOpen.value = true
  }

  async function deletePinFromMenu () {
    const pinId = pinMenuPinId.value
    pinMenuOpen.value = false
    if (!pinId || !entity.value) return
    try {
      entity.value = await deleteMapPin(worldId.value, entity.value.id, pinId)
    } catch {
      actionError.value = 'Failed to delete pin'
    }
  }

  async function handlePinMove (pinId: string, x: number, y: number) {
    if (!entity.value) return
    try {
      entity.value = await updateMapPin(worldId.value, entity.value.id, pinId, { x, y })
    } catch {
      actionError.value = 'Failed to move pin'
    }
  }

  async function handlePinPickerSelect (pinnedEntityId: string) {
    pinPickerOpen.value = false
    if (!entity.value) return
    try {
      if (pinPickerMode.value === 'add' && pendingPinCoords.value) {
        entity.value = await addMapPin(
          worldId.value, entity.value.id, pinnedEntityId, pendingPinCoords.value.x, pendingPinCoords.value.y,
        )
      } else if (pinPickerMode.value === 'rebind' && pinMenuPinId.value) {
        entity.value = await updateMapPin(worldId.value, entity.value.id, pinMenuPinId.value, {
          entityId: pinnedEntityId,
        })
      }
    } catch {
      actionError.value = 'Failed to update map'
    }
  }

  async function handlePinPickerCreate (name: string) {
    pinPickerOpen.value = false
    if (!entity.value) return
    try {
      // Parented under the map entity itself, not the world root - creating a pin target doesn't
      // require world ownership the way a root-level entity would.
      const created = await createEntity(worldId.value, name, entity.value.id)
      await handlePinPickerSelect(created.id)
      await refreshWorldEntities()
      await refreshNavItems?.()
    } catch {
      actionError.value = 'Failed to create entity'
    }
  }

  function handleArticleChange (markdown: string) {
    draftMarkdown.value = markdown
  }

  async function handleSaveArticle () {
    if (!entity.value) return
    savingArticle.value = true
    try {
      await setArticle(worldId.value, entity.value.id, draftMarkdown.value)
      savedMarkdown.value = draftMarkdown.value
    } finally {
      savingArticle.value = false
    }
  }

  async function confirmDiscardIfDirty (): Promise<boolean> {
    if (!articleDirty.value) return true
    return await confirmDialog({
      title: 'Unsaved changes',
      message: 'You have unsaved changes. Leave without saving?',
      confirmText: 'Leave',
      cancelText: 'Stay',
    })
  }

  onBeforeRouteUpdate(() => confirmDiscardIfDirty())
  onBeforeRouteLeave(() => confirmDiscardIfDirty())

  function handleBeforeUnload (event: BeforeUnloadEvent) {
    if (articleDirty.value) {
      event.preventDefault()
    }
  }

  onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', handleBeforeUnload))
</script>

<style scoped>
.entity-content {
  min-height: 0;
  scrollbar-width: none;
}

.entity-content::-webkit-scrollbar {
  display: none;
}
</style>
