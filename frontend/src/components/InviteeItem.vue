<template>
  <v-list-item :subtitle="subtitle ?? invite.inviteeEmail">
    <template #prepend>
      <IdenticonAvatar :seed="invite.inviteeEmail" />
    </template>

    <template #title>
      <div class="d-flex align-center ga-2">
        <span>{{ displayName }}</span>

        <v-tooltip v-if="!invite.accepted" text="Pending">
          <template #activator="{ props: tooltipProps }">
            <v-icon color="warning" icon="mdi-timer-sand-paused" size="small" v-bind="tooltipProps" />
          </template>
        </v-tooltip>
      </div>
    </template>

    <template v-if="$slots.append" #append>
      <slot name="append" />
    </template>
  </v-list-item>
</template>

<script lang="ts" setup>
  import type { InviteSummary } from '@/types/invite'
  import { computed } from 'vue'
  import { anonymousName } from '@/utils/anonymousName'
  import IdenticonAvatar from './IdenticonAvatar.vue'

  const props = defineProps<{
    invite: InviteSummary
    subtitle?: string
  }>()

  const displayName = computed(() => props.invite.inviteeName ?? anonymousName(props.invite.inviteeEmail))
</script>
