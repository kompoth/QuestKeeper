<template>
  <v-navigation-drawer v-if="$slots.sidebar" v-model="drawer" :temporary="mobile" width="320">
    <template #prepend>
      <div class="d-flex align-center ga-2 pa-3">
        <Logo :size="40" />

        <div>
          <div class="text-h6">{{ appTitle }}</div>
          <div v-if="appSubtitle" class="text-caption text-medium-emphasis">{{ appSubtitle }}</div>
        </div>

        <v-spacer />

        <v-btn
          v-if="route.path !== '/w'"
          aria-label="Back to worlds"
          icon="mdi-chevron-left"
          to="/w"
          variant="text"
        />
      </div>

      <v-divider />
    </template>

    <slot name="sidebar" />

    <template #append>
      <v-divider />

      <div class="d-flex align-center ga-0 px-3 py-2">
        <div class="d-flex align-center ga-3" style="min-width: 0;">
          <MemberItem
            v-if="currentUser"
            class="px-0"
            density="compact"
            style="min-width: 0;"
            :user="currentUser"
          />
        </div>

        <slot name="bottom-actions" />

        <v-spacer />

        <v-menu>
          <template #activator="{ props: menuProps }">
            <v-btn icon="mdi-dots-vertical" variant="text" v-bind="menuProps" />
          </template>

          <v-list density="compact">
            <v-list-item
              v-if="currentUser?.role === 'admin'"
              prepend-icon="mdi-wizard-hat"
              title="Admin panel"
              to="/admin"
            />

            <v-list-item
              :prepend-icon="theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
              :title="theme.global.current.value.dark ? 'Light mode' : 'Dark mode'"
              @click="toggle"
            />

            <v-list-item prepend-icon="mdi-logout" title="Log out" @click="emit('logout')" />
          </v-list>
        </v-menu>
      </div>
    </template>
  </v-navigation-drawer>

  <v-app-bar v-if="mobile && $slots.sidebar">
    <v-app-bar-nav-icon @click="drawer = !drawer" />

    <v-spacer />

    <ThemeToggle />
    <v-btn aria-label="Log out" icon="mdi-logout" variant="text" @click="emit('logout')" />
  </v-app-bar>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useDisplay } from 'vuetify'
  import { useAuth } from '@/composables/useAuth'
  import { useThemeMode } from '@/composables/useThemeMode'
  import Logo from './Logo.vue'
  import MemberItem from './MemberItem.vue'
  import ThemeToggle from './ThemeToggle.vue'

  defineProps<{
    appTitle: string
    appSubtitle?: string
  }>()

  const emit = defineEmits<{
    logout: []
  }>()

  const { currentUser } = useAuth()
  const { theme, toggle } = useThemeMode()

  const route = useRoute()

  const { mobile } = useDisplay()

  const drawer = ref(!mobile.value)

  watch(mobile, isMobile => {
    drawer.value = !isMobile
  })
</script>
