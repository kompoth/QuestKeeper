<template>
  <div class="text-headline-small text-center mb-6">Sign in</div>

  <v-form @submit.prevent="handleLogin">
    <v-alert
      v-if="error"
      class="mb-4"
      closable
      type="error"
      @click:close="error = undefined"
    >{{ error }}</v-alert>

    <v-text-field v-model="email" label="Email" type="email" />
    <v-text-field v-model="password" label="Password" type="password" />

    <div class="d-flex flex-column">
      <v-btn color="primary" :loading="submitting" type="submit" variant="flat">Sign in</v-btn>
      <v-btn class="mt-2" to="/login/password-recovery" variant="flat">Forgot password?</v-btn>
    </div>
  </v-form>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { ApiError } from '@/api/client'
  import { useAuth } from '@/composables/useAuth'

  const router = useRouter()
  const { login } = useAuth()

  const email = ref('')
  const password = ref('')
  const error = ref<string>()
  const submitting = ref(false)

  async function handleLogin () {
    error.value = undefined
    submitting.value = true
    try {
      await login(email.value, password.value)
      router.push('/w')
    } catch (error_) {
      error.value = error_ instanceof ApiError && error_.status === 401
        ? 'Invalid email or password'
        : 'Something went wrong, please try again'
    } finally {
      submitting.value = false
    }
  }
</script>
