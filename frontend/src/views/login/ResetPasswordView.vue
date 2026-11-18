<template>
  <div class="text-headline-small text-center mb-6">Set a new password</div>

  <v-form @submit.prevent="handleSubmit">
    <v-alert
      v-if="error"
      class="mb-4"
      closable
      type="error"
      @click:close="error = undefined"
    >{{ error }}</v-alert>

    <v-alert v-if="success" class="mb-4" type="success">Password set. You can now sign in.</v-alert>

    <template v-if="!success">
      <v-text-field v-model="newPassword" label="New password" type="password" />
      <v-text-field v-model="confirmPassword" label="Confirm new password" type="password" />

      <div class="d-flex flex-column">
        <v-btn color="primary" :loading="submitting" type="submit" variant="flat">Set password</v-btn>
      </div>
    </template>

    <v-btn v-else class="mt-2" to="/login" variant="flat">Back to Sign in</v-btn>
  </v-form>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { resetPassword } from '@/api/auth'
  import { ApiError } from '@/api/client'

  const route = useRoute()
  const token = route.query.token as string | undefined

  const newPassword = ref('')
  const confirmPassword = ref('')
  const error = ref<string>()
  const submitting = ref(false)
  const success = ref(false)

  async function handleSubmit () {
    error.value = undefined

    if (!token) {
      error.value = 'This link is invalid or has expired'
      return
    }

    if (newPassword.value !== confirmPassword.value) {
      error.value = 'Passwords do not match'
      return
    }

    submitting.value = true
    try {
      await resetPassword(token, newPassword.value)
      success.value = true
    } catch (error_) {
      error.value = error_ instanceof ApiError && error_.status === 404
        ? 'This link is invalid or has expired'
        : 'Something went wrong, please try again'
    } finally {
      submitting.value = false
    }
  }
</script>
