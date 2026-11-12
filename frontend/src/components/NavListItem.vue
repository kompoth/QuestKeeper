<template>
  <v-list-item :prepend-icon="item.icon" :title="item.title" :to="item.to">
    <template v-if="hasChildren" #append>
      <v-icon :icon="expanded ? 'mdi-chevron-up' : 'mdi-chevron-down'" @click.stop.prevent="expanded = !expanded" />
    </template>
  </v-list-item>

  <div v-if="hasChildren" v-show="expanded" class="pl-4">
    <NavListItem v-for="child in item.children" :key="child.id" :item="child" />
  </div>
</template>

<script lang="ts" setup>
  import type { NavItem } from '@/types/nav-item'
  import { computed, ref } from 'vue'

  const props = defineProps<{
    item: NavItem
  }>()

  const hasChildren = computed(() => !!props.item.children?.length)

  const expanded = ref(false)
</script>
