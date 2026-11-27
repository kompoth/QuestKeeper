<template>
  <v-card :title="title">
    <v-card-text>
      <v-autocomplete
        v-model="selected"
        clearable
        item-title="name"
        item-value="id"
        :items="entities"
        label="Search entities"
        variant="outlined"
      />

      <v-divider class="my-4" />

      <div class="text-subtitle-2 mb-2">Or create a new entity</div>

      <div class="d-flex ga-2">
        <v-text-field
          v-model="newName"
          density="compact"
          hide-details
          label="Name"
          variant="outlined"
        />

        <v-btn :disabled="!newName" @click="handleCreate">Create</v-btn>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn @click="emit('cancel')">Cancel</v-btn>
      <v-btn color="primary" :disabled="!selected" @click="handleSelect">Choose</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
  import type { Entity } from '@/types/entity'
  import { ref } from 'vue'

  defineProps<{
    title: string
    entities: Entity[]
  }>()

  const emit = defineEmits<{
    select: [entityId: string]
    create: [name: string]
    cancel: []
  }>()

  const selected = ref<string>()
  const newName = ref('')

  function handleSelect () {
    if (selected.value) emit('select', selected.value)
  }

  function handleCreate () {
    if (newName.value) emit('create', newName.value)
  }
</script>
