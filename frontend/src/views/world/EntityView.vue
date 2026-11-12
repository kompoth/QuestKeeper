<template>
  <v-container class="pa-0 fill-height d-flex flex-column" fluid>
    <p v-if="!entity">Entity not found.</p>

    <template v-else>
      <v-tabs v-model="tab" bg-color="surface" class="flex-shrink-0" slider-color="primary">
        <v-tab
          v-for="name in tabNames"
          :key="name"
          :class="tab === name ? 'text-high-emphasis' : 'text-medium-emphasis'"
          :value="name"
        >
          {{ name }}
        </v-tab>

        <!-- TODO: tab creation -->
        <v-tab disabled prepend-icon="mdi-plus" value="new-tab">New tab</v-tab>
      </v-tabs>

      <v-tabs-window v-model="tab" class="flex-1-1-100 overflow-hidden">
        <v-tabs-window-item v-for="(entityTab, name) in entity.tabs" :key="name" class="fill-height" :value="name">
          <EntityMap v-if="entityTab.kind === 'map'" :map="entityTab.map" @open="openEntity" />
          <EntityArticle v-else :editable="true" :model-value="entityTab.content" />
        </v-tabs-window-item>
      </v-tabs-window>
    </template>
  </v-container>
</template>

<script lang="ts" setup>
  import type { Entity } from '@/types/entity'
  import { computed, ref, watchEffect } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import EntityArticle from '@/components/EntityArticle.vue'
  import EntityMap from '@/components/EntityMap.vue'
  import { getEntity } from '@/data/entities'
  import { listEntityTabs } from '@/types/entity'

  const route = useRoute()
  const router = useRouter()

  const entity = ref<Entity>()

  const tabNames = computed(() => entity.value ? Object.keys(listEntityTabs(entity.value)) : [])

  const tab = ref<string>()

  watchEffect(async () => {
    entity.value = await getEntity(route.params.entityId as string)
    tab.value = tabNames.value[0]
  })

  function openEntity (entityId: string) {
    router.push(`/w/${route.params.worldId}/e/${entityId}`)
  }
</script>

<style scoped>
.v-tabs-window {
  min-height: 0;
}

:deep(.v-window__container) {
  height: 100%;
}
</style>
