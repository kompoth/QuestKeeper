<template>
  <v-dialog v-model="confirmDialogOpen" width="400">
    <v-card>
      <v-card-title>{{ confirmDialogTitle }}</v-card-title>
      <v-card-text>{{ confirmDialogMessage }}</v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="rejectConfirm">{{ confirmDialogCancelText }}</v-btn>
        <v-btn color="primary" variant="flat" @click="acceptConfirm">{{ confirmDialogConfirmText }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
  import { useConfirmDialog } from '@/composables/useConfirmDialog'

  const {
    confirmDialogOpen,
    confirmDialogTitle,
    confirmDialogMessage,
    confirmDialogConfirmText,
    confirmDialogCancelText,
    acceptConfirm,
    rejectConfirm,
  } = useConfirmDialog()
</script>
