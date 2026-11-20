<template>
  <v-app-bar v-if="mobile && $slots.sidebar">
    <v-app-bar-nav-icon @click="drawer = !drawer" />

    <div class="flex-grow-1 text-truncate" style="min-width: 0;">
      <div class="text-subtitle-1 text-truncate">{{ appTitle }}</div>
      <div v-if="appSubtitle" class="text-caption text-medium-emphasis text-truncate">{{ appSubtitle }}</div>
    </div>

    <v-btn
      v-if="showBackButton"
      class="flex-shrink-0"
      prepend-icon="mdi-chevron-left"
      to="/w"
      variant="text"
    >
      Back to worlds
    </v-btn>

    <AccountMenu @logout="emit('logout')">
      <template #activator="{ props: menuProps }">
        <v-btn icon variant="text" v-bind="menuProps">
          <IdenticonAvatar v-if="currentUser" :seed="currentUser.email" />
        </v-btn>
      </template>
    </AccountMenu>
  </v-app-bar>

  <v-navigation-drawer
    v-if="$slots.sidebar"
    v-model="drawer"
    :location="mobile ? 'top' : undefined"
    :temporary="mobile"
    :width="mobile ? '70%' : 320"
  >
    <template v-if="!mobile" #prepend>
      <div class="d-flex align-center ga-2 pa-3">
        <Logo :size="40" />

        <div style="min-width: 0;">
          <div class="text-h6 text-truncate">{{ appTitle }}</div>
          <div v-if="appSubtitle" class="text-caption text-medium-emphasis text-truncate">{{ appSubtitle }}</div>
        </div>

        <v-spacer />

        <v-btn
          v-if="showBackButton"
          class="flex-shrink-0"
          prepend-icon="mdi-chevron-left"
          to="/w"
          variant="text"
        >
          Back to worlds
        </v-btn>
      </div>

      <v-divider />
    </template>

    <slot name="sidebar" />

    <template v-if="!mobile" #append>
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

        <AccountMenu @logout="emit('logout')">
          <template #activator="{ props: menuProps }">
            <v-btn icon="mdi-dots-vertical" variant="text" v-bind="menuProps" />
          </template>
        </AccountMenu>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue'
  import { useDisplay } from 'vuetify'
  import { useAuth } from '@/composables/useAuth'
  import AccountMenu from './AccountMenu.vue'
  import IdenticonAvatar from './IdenticonAvatar.vue'
  import Logo from './Logo.vue'
  import MemberItem from './MemberItem.vue'

  defineProps<{
    appTitle: string
    appSubtitle?: string
    showBackButton?: boolean
  }>()

  const emit = defineEmits<{
    logout: []
  }>()

  const { currentUser } = useAuth()

  const { mobile } = useDisplay()

  const drawer = ref(!mobile.value)

  watch(mobile, isMobile => {
    drawer.value = !isMobile
  })
</script>
