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
          <v-chip v-if="entity.access.write" label @click="startRename">
            <v-icon icon="mdi-form-textbox" start />
            Rename
          </v-chip>

          <v-chip
            v-if="entity.access.write"
            :color="entityEditable ? 'primary' : 'default'"
            label
            @click="entityEditable = !entityEditable"
          >
            <v-icon :icon="entityEditable ? 'mdi-pencil' : 'mdi-text-long'" start />
            {{ entityEditable ? 'Edit mode' : 'Reading mode' }}
          </v-chip>
        </div>
      </v-toolbar>

      <div class="entity-content flex-1-1-100 overflow-y-auto">
        <EntityMap v-if="entity.map" :map="entity.map" @open="openEntity" />

        <EntityArticle
          v-else
          :editable="entityEditable"
          :model-value="entity.article?.markdown ?? ''"
          @update:model-value="handleArticleChange"
        />
      </div>
    </template>
  </v-container>
</template>

<script lang="ts" setup>
  import type { Entity } from '@/types/entity'
  import { computed, inject, onBeforeUnmount, ref, watchEffect } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { getEntity, renameEntity, setArticle } from '@/api/entities'
  import EntityArticle from '@/components/EntityArticle.vue'
  import EntityMap from '@/components/EntityMap.vue'
  import { useRenameDialog } from '@/composables/useRenameDialog'
  import { refreshNavItemsKey } from '@/utils/nav'

  const ARTICLE_SAVE_DEBOUNCE_MS = 500

  interface BreadcrumbItem {
    title: string
    to?: string
    disabled?: boolean
  }

  const route = useRoute()
  const router = useRouter()

  const worldId = computed(() => route.params.worldId as string)

  const entityEditable = ref(false)

  const { openRenameDialog } = useRenameDialog()
  const refreshNavItems = inject(refreshNavItemsKey)

  const entity = ref<Entity>()
  const entityPath = ref<Entity[]>([])

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
    entity.value = await getEntity(worldId.value, route.params.entityId as string)
    entityPath.value = entity.value ? await getEntityPath(entity.value) : []
  }

  watchEffect(refreshEntity)

  function openEntity (entityId: string) {
    router.push(`/w/${worldId.value}/e/${entityId}`)
  }

  async function startRename () {
    if (!entity.value) return
    const title = await openRenameDialog(entity.value.name)
    if (title === undefined) return
    await renameEntity(worldId.value, entity.value.id, title)
    await refreshEntity()
    await refreshNavItems?.()
  }

  let articleSaveTimeout: ReturnType<typeof setTimeout> | undefined

  function handleArticleChange (markdown: string) {
    if (!entity.value) return
    const entityId = entity.value.id
    const currentWorldId = worldId.value
    clearTimeout(articleSaveTimeout)
    articleSaveTimeout = setTimeout(() => {
      setArticle(currentWorldId, entityId, markdown)
    }, ARTICLE_SAVE_DEBOUNCE_MS)
  }

  onBeforeUnmount(() => {
    clearTimeout(articleSaveTimeout)
  })
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
