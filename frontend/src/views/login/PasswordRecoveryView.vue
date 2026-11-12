<template>
  <div class="text-headline-small text-center mb-6">Recover password</div>

  <v-form>
    <v-text-field label="Email" type="email" />
  </v-form>

  <div class="d-flex flex-column">
    <v-btn color="primary" variant="flat">Send recovery link</v-btn>
    <v-btn class="mt-2" to="/login" variant="flat">Back to Sign in</v-btn>
  </div>
</template>

<script lang="ts" setup>
//
</script>
