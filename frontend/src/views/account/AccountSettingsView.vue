<template>
  <v-container>
    <h1 class="text-h5 mb-4">My Account</h1>

    <IdenticonAvatar :avatar-url="currentUser?.avatar" :seed="currentUser?.email ?? ''" :size="96" />

    <div class="mt-2 mb-6">
      <v-btn :loading="uploadingAvatar" prepend-icon="mdi-upload" variant="tonal" @click="fileInput?.click()">
        Change image
      </v-btn>

      <input
        ref="fileInput"
        accept="image/png,image/jpeg,image/webp,image/gif"
        hidden
        type="file"
        @change="handleAvatarSelected"
      >
    </div>

    <v-text-field v-model="name" label="Name" variant="outlined" />
    <v-text-field disabled label="Email" :model-value="currentUser?.email" variant="outlined" />

    <v-btn
      class="mb-6"
      color="primary"
      :loading="saving"
      variant="flat"
      @click="handleSave"
    >Save</v-btn>

    <div>
      <v-btn prepend-icon="mdi-lock-reset" to="/login/password-recovery" variant="outlined">Reset password</v-btn>
    </div>

    <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
  </v-container>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { setAvatar, uploadAvatar } from '@/api/avatar'
  import { updateName } from '@/api/profile'
  import IdenticonAvatar from '@/components/IdenticonAvatar.vue'
  import { useAuth } from '@/composables/useAuth'
  import { useSnackbar } from '@/composables/useSnackbar'

  const { currentUser } = useAuth()
  const { snackbar, snackbarText, snackbarColor, notify } = useSnackbar()

  const name = ref(currentUser.value?.name ?? '')
  const saving = ref(false)
  const uploadingAvatar = ref(false)
  const fileInput = ref<HTMLInputElement>()

  async function handleSave () {
    saving.value = true
    try {
      currentUser.value = await updateName(name.value)
      notify('Saved', 'success')
    } catch {
      notify('Failed to update name', 'error')
    } finally {
      saving.value = false
    }
  }

  async function handleAvatarSelected (event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) {
      return
    }
    uploadingAvatar.value = true
    try {
      const fileId = await uploadAvatar(file)
      currentUser.value = await setAvatar(fileId)
    } catch {
      notify('Failed to update avatar', 'error')
    } finally {
      uploadingAvatar.value = false
      ;(event.target as HTMLInputElement).value = ''
    }
  }
</script>
