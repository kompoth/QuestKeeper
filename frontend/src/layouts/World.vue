<template>
  <NavBar :app-title="appTitle" back-to="/w" :items="navItems" @logout="handleLogout" />

  <v-main>
    <router-view :key="route.fullPath" />
  </v-main>
</template>

<script lang="ts" setup>
  import type { NavItem } from '@/types/nav-item'
  import { computed, ref, watchEffect } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import NavBar from '@/components/NavBar.vue'
  import { listEntities } from '@/data/entities'
  import { getWorld } from '@/data/worlds'
  import { toNavItem } from '@/utils/nav'

  const route = useRoute()
  const router = useRouter()

  const worldId = computed(() => route.params.worldId as string)

  const appTitle = computed(() => getWorld(worldId.value)?.name ?? 'Questkeeper')

  const navItems = ref<NavItem[]>([])

  watchEffect(async () => {
    const entities = await listEntities(worldId.value)
    navItems.value = [
      ...await Promise.all(entities.map(entity => toNavItem(worldId.value, entity))),
      // TODO: entity creation
      { id: 'new-entity', title: 'New entity', icon: 'mdi-plus' },
    ]
  })

  function handleLogout () {
    router.push('/login')
  }
</script>
