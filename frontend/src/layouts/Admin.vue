<template>
  <v-app-bar>
    <v-btn icon="mdi-arrow-left" to="/w" variant="text" />
    <v-app-bar-title>Admin</v-app-bar-title>

    <template #extension>
      <v-tabs grow>
        <v-tab to="/admin/settings">Settings</v-tab>
        <v-tab to="/admin/users">Users</v-tab>
      </v-tabs>
    </template>
  </v-app-bar>

  <v-main scrollable>
    <v-container>
      <router-view />
    </v-container>
  </v-main>
</template>

<script lang="ts" setup>
//
</script>
