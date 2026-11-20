<template>
  <v-text-field
    v-model="search"
    class="ma-2"
    clearable
    density="compact"
    hide-details
    label="Search"
    prepend-inner-icon="mdi-magnify"
    variant="outlined"
  />

  <v-treeview
    density="compact"
    indent-lines
    :item-props="item => ({ prependIcon: item.icon, to: item.to, onClick: item.onClick })"
    item-value="id"
    :items="items"
    :search="search"
  >
    <template #append="{ item }">
      <v-menu v-if="item.actions?.length">
        <template #activator="{ props: menuProps }">
          <v-btn
            icon="mdi-dots-vertical"
            size="small"
            variant="text"
            v-bind="menuProps"
            @click.stop.prevent
          />
        </template>

        <v-list density="compact">
          <v-list-item
            v-for="action in item.actions"
            :key="action.title"
            :class="action.color ? `text-${action.color}` : undefined"
            :prepend-icon="action.icon"
            :title="action.title"
            @click="action.onClick"
          />
        </v-list>
      </v-menu>
    </template>
  </v-treeview>
</template>

<script lang="ts" setup>
  import type { NavItem } from '@/types/nav-item'
  import { ref } from 'vue'

  defineProps<{
    items: NavItem[]
  }>()

  const search = ref('')
</script>
