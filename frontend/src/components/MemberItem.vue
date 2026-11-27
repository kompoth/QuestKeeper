<template>
  <v-list-item :subtitle="user.email">
    <template #prepend>
      <IdenticonAvatar :avatar-url="user.avatar" :seed="user.email" />
    </template>

    <template #title>
      <div class="d-flex align-center ga-2">
        <span>{{ user.name }}</span>

        <v-tooltip v-if="roleChip.icon" :text="user.role">
          <template #activator="{ props: tooltipProps }">
            <v-icon :color="roleChip.color" :icon="roleChip.icon" size="small" v-bind="tooltipProps" />
          </template>
        </v-tooltip>

        <v-tooltip v-if="user.status === 'pending'" text="Pending">
          <template #activator="{ props: tooltipProps }">
            <v-icon color="warning" icon="mdi-timer-sand-paused" size="small" v-bind="tooltipProps" />
          </template>
        </v-tooltip>
      </div>
    </template>
  </v-list-item>
</template>

<script lang="ts" setup>
  import type { User, UserRole } from '@/types/user'
  import { computed } from 'vue'
  import IdenticonAvatar from './IdenticonAvatar.vue'

  const ROLE_CHIPS: Record<UserRole, { icon?: string, color: string }> = {
    admin: { icon: 'mdi-security', color: 'green' },
    warden: { icon: 'mdi-shield-crown-outline', color: 'amber' },
    member: { color: 'secondary' },
  }

  const props = defineProps<{
    user: User
  }>()

  const roleChip = computed(() => ROLE_CHIPS[props.user.role])
</script>
