<template>
  <div class="text-headline-small text-center mb-6">Sign in</div>

  <v-form>
    <v-text-field label="Email" type="email" />
    <v-text-field label="Password" type="password" />

    <div class="d-flex flex-column">
      <v-btn color="primary" variant="flat" @click="handleLogin">Sign in</v-btn>
      <v-btn class="mt-2" to="/login/password-recovery" variant="flat">Forgot password?</v-btn>
    </div>
  </v-form>
</template>

<script lang="ts" setup>
  import { useRouter } from 'vue-router'

  const router = useRouter()

  function handleLogin () {
    router.push('/w')
  }
</script>
