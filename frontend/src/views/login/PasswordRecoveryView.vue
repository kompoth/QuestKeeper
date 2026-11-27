<template>
  <div class="text-headline-small text-center mb-6">Recover password</div>

  <v-form @submit.prevent="handleSubmit">
    <v-alert
      v-if="error"
      class="mb-4"
      closable
      type="error"
      @click:close="error = undefined"
    >{{ error }}</v-alert>

    <v-alert v-if="submitted" class="mb-4" type="success">
      If an account exists for that email, a recovery link has been sent.
    </v-alert>

    <template v-if="!submitted">
      <v-text-field v-model="email" label="Email" type="email" />

      <div class="d-flex flex-column">
        <v-btn color="primary" :loading="submitting" type="submit" variant="flat">Send recovery link</v-btn>
        <v-btn class="mt-2" to="/login" variant="flat">Back to Sign in</v-btn>
      </div>
    </template>

    <v-btn v-else class="mt-2" to="/login" variant="flat">Back to Sign in</v-btn>
  </v-form>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { requestPasswordRecovery } from '@/api/auth'
  import { ApiError } from '@/api/client'

  const email = ref('')
  const error = ref<string>()
  const submitting = ref(false)
  const submitted = ref(false)

  async function handleSubmit () {
    error.value = undefined
    submitting.value = true
    try {
      await requestPasswordRecovery(email.value)
      submitted.value = true
    } catch (error_) {
      error.value = error_ instanceof ApiError && error_.status === 403
        ? error_.detail
        : 'Something went wrong, please try again'
    } finally {
      submitting.value = false
    }
  }
</script>
