<template>
  <v-container>
    <h1 class="text-h5 mb-4">Members</h1>

    <v-data-table
      class="mb-4"
      :headers="headers"
      :items="invites"
      :loading="loading"
    >
      <template #item.member="{ item }">
        <InviteeItem :invite="item" />
      </template>

      <template #item.actions="{ item }">
        <v-btn color="error" size="small" variant="tonal" @click="handleExpel(item)">Expel</v-btn>
      </template>
    </v-data-table>

    <v-divider class="mb-4" />

    <div class="text-subtitle-1 font-weight-bold mb-2">Invite someone</div>

    <v-alert
      v-if="inviteError"
      class="mb-4"
      closable
      type="error"
      @click:close="inviteError = undefined"
    >{{ inviteError }}</v-alert>

    <div class="d-flex align-center ga-4">
      <v-text-field
        v-model="inviteEmail"
        hide-details
        label="Email"
        prepend-inner-icon="mdi-email-outline"
        type="email"
        variant="outlined"
      />

      <v-btn
        color="primary"
        :disabled="!canSendInvite"
        :loading="inviteSubmitting"
        variant="flat"
        @click="handleSendInvite"
      >
        Send invite
      </v-btn>
    </div>

    <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
  </v-container>
</template>

<script lang="ts" setup>
  import type { InviteSummary } from '@/types/invite'
  import { computed, onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { ApiError } from '@/api/client'
  import { createInvite, expelInvitee, listInvites } from '@/api/invites'
  import InviteeItem from '@/components/InviteeItem.vue'

  const route = useRoute()
  const worldId = route.params.worldId as string

  const headers = [
    { title: 'Member', key: 'member', sortable: false },
    { title: 'Actions', key: 'actions', sortable: false },
  ]

  const invites = ref<InviteSummary[]>([])
  const loading = ref(false)

  const inviteEmail = ref('')
  const inviteError = ref<string>()
  const inviteSubmitting = ref(false)

  const snackbar = ref(false)
  const snackbarText = ref('')
  const snackbarColor = ref('success')

  const canSendInvite = computed(() => inviteEmail.value !== '')

  function notify (text: string, color: string) {
    snackbarText.value = text
    snackbarColor.value = color
    snackbar.value = true
  }

  async function refreshInvites () {
    loading.value = true
    try {
      invites.value = await listInvites(worldId)
    } finally {
      loading.value = false
    }
  }

  onMounted(refreshInvites)

  async function handleSendInvite () {
    if (!canSendInvite.value) return
    inviteError.value = undefined
    inviteSubmitting.value = true
    try {
      await createInvite(worldId, inviteEmail.value)
      inviteEmail.value = ''
      await refreshInvites()
    } catch (error) {
      inviteError.value = error instanceof ApiError ? error.detail : 'Something went wrong, please try again'
    } finally {
      inviteSubmitting.value = false
    }
  }

  async function handleExpel (invite: InviteSummary) {
    try {
      await expelInvitee(worldId, invite.inviteeEmail)
      await refreshInvites()
      notify(`${invite.inviteeEmail} expelled`, 'success')
    } catch {
      notify('Failed to expel member', 'error')
    }
  }
</script>
