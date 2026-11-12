<template>
  <v-app-bar>
    <v-btn v-if="backTo" icon="mdi-arrow-left" :to="backTo" variant="text" />
    <v-app-bar-nav-icon v-if="items.length > 0" @click="drawer = !drawer" />
    <v-app-bar-title>{{ appTitle }}</v-app-bar-title>

    <v-spacer />

    <div class="d-flex ga-1 mr-2">
      <ThemeToggle />
      <v-btn aria-label="Log out" icon="mdi-logout" variant="text" @click="emit('logout')" />
    </div>
  </v-app-bar>

  <v-navigation-drawer v-if="items.length > 0" v-model="drawer" :temporary="mobile">
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

    <v-list density="compact" nav>
      <NavListItem v-for="item in filteredItems" :key="item.id" :item="item" />
    </v-list>
  </v-navigation-drawer>
</template>

<script lang="ts" setup>
  import type { NavItem } from '@/types/nav-item'
  import { computed, ref, watch } from 'vue'
  import { useDisplay } from 'vuetify'
  import NavListItem from './NavListItem.vue'
  import ThemeToggle from './ThemeToggle.vue'

  const props = withDefaults(defineProps<{
    items?: NavItem[]
    appTitle: string
    backTo?: string
  }>(), {
    items: () => [],
  })

  const emit = defineEmits<{
    logout: []
  }>()

  const search = ref('')

  function flattenItems (items: NavItem[]): NavItem[] {
    return items.flatMap(item => [item, ...(item.children ? flattenItems(item.children) : [])])
  }

  const filteredItems = computed(() => {
    const query = search.value.trim().toLowerCase()
    if (!query) return props.items
    return flattenItems(props.items)
      .filter(item => item.title.toLowerCase().includes(query))
      .map(item => ({ ...item, children: undefined }))
  })

  const { mobile } = useDisplay()

  const drawer = ref(!mobile.value)

  watch(mobile, isMobile => {
    drawer.value = !isMobile
  })
</script>
