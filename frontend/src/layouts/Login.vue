<template>
  <v-main>

    <v-container class="d-flex align-center justify-center" style="min-height: 100vh;">
      <v-card class="pa-8" max-width="420" width="100%">
        <v-card-text>
          <router-view />
        </v-card-text>
      </v-card>
    </v-container>
  </v-main>
</template>

<script lang="ts" setup>
//
</script>
