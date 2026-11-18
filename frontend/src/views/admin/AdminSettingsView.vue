<template>
  <h1 class="text-h5 mb-4">Runtime settings</h1>

  <v-switch
    v-model="registrationEnabled"
    hide-details
    label="Open self-registration"
    @update:model-value="save"
  />

  <v-switch
    v-model="passwordResetEnabled"
    hide-details
    label="Password reset"
    @update:model-value="save"
  />

  <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { getRuntimeSettings, updateRuntimeSettings } from '@/api/admin'

  const registrationEnabled = ref(true)
  const passwordResetEnabled = ref(true)

  const snackbar = ref(false)
  const snackbarText = ref('')
  const snackbarColor = ref('success')

  onMounted(async () => {
    const settings = await getRuntimeSettings()
    registrationEnabled.value = settings.registrationEnabled
    passwordResetEnabled.value = settings.passwordResetEnabled
  })

  async function save () {
    try {
      await updateRuntimeSettings({
        registrationEnabled: registrationEnabled.value,
        passwordResetEnabled: passwordResetEnabled.value,
      })
      snackbarColor.value = 'success'
      snackbarText.value = 'Settings saved'
    } catch {
      snackbarColor.value = 'error'
      snackbarText.value = 'Failed to save settings'
    }
    snackbar.value = true
  }
</script>
