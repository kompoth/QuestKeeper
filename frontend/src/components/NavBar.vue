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

  <v-navigation-drawer v-if="items.length > 0" v-model="drawer" :temporary="mobile" width="300">
    <template #prepend>
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
    </template>

    <v-treeview
      density="compact"
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
              :prepend-icon="action.icon"
              :title="action.title"
              @click="action.onClick"
            />
          </v-list>
        </v-menu>
      </template>
    </v-treeview>
  </v-navigation-drawer>
</template>

<script lang="ts" setup>
  import type { NavItem } from '@/types/nav-item'
  import { ref, watch } from 'vue'
  import { useDisplay } from 'vuetify'
  import ThemeToggle from './ThemeToggle.vue'

  withDefaults(defineProps<{
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

  const { mobile } = useDisplay()

  const drawer = ref(!mobile.value)

  watch(mobile, isMobile => {
    drawer.value = !isMobile
  })
</script>
