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
        v-if="uploadError"
        class="mx-4 mt-2"
        closable
        type="error"
        @click:close="uploadError = undefined"
      >{{ uploadError }}</v-alert>

      <div class="entity-content flex-1-1-100 overflow-y-auto">
        <EntityMap v-if="entity.map" :map="entity.map" @open="openEntity" />

        <template v-else>
          <EntityArticle
            class="pa-4"
            :editable="articleEditable"
            :entity-id="entity.id"
            :model-value="savedMarkdown"
            :world-id="worldId"
            @update:model-value="handleArticleChange"
            @upload-error="uploadError = $event"
          />
        </template>
      </div>
    </template>
  </v-container>
</template>

<script lang="ts" setup>
  import type { Entity } from '@/types/entity'
  import { computed, inject, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
  import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
  import { getEntity, setArticle } from '@/api/entities'
  import EntityArticle from '@/components/EntityArticle.vue'
  import EntityMap from '@/components/EntityMap.vue'
  import { useConfirmDialog } from '@/composables/useConfirmDialog'
  import { entityTrashVersionKey } from '@/utils/nav'

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

  const entity = ref<Entity>()
  const entityPath = ref<Entity[]>([])
  const uploadError = ref<string>()
  const articleEditable = computed(() => entityEditable.value && !entity.value?.deletedAt)

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

  async function refreshEntity () {
    const fetchedEntity = await getEntity(worldId.value, route.params.entityId as string)
    // Set together, synchronously, so EntityArticle never mounts with a stale/empty model-value
    // between `entity` updating and `savedMarkdown` catching up (no `await` in between).
    entity.value = fetchedEntity
    savedMarkdown.value = fetchedEntity?.article?.markdown ?? ''
    draftMarkdown.value = savedMarkdown.value

    entityPath.value = fetchedEntity ? await getEntityPath(fetchedEntity) : []
  }

  watchEffect(() => {
    void entityTrashVersion?.value // read so a trash/restore/purge elsewhere also triggers a re-fetch here
    refreshEntity()
  })

  function openEntity (entityId: string) {
    router.push(`/w/${worldId.value}/e/${entityId}`)
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
