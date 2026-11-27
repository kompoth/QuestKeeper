<template>
  <v-tabs v-model="tab" density="compact" grow hide-slider>
    <v-tab
      v-for="sidebarTab in tabs"
      :key="sidebarTab.value"
      :aria-label="sidebarTab.label"
      :class="{ 'opacity-50': tab !== sidebarTab.value }"
      :disabled="sidebarTab.disabled"
      min-width="0"
      :value="sidebarTab.value"
    >
      <v-icon :icon="sidebarTab.icon" size="medium" />
    </v-tab>
  </v-tabs>

  <v-tabs-window v-model="tab">
    <v-tabs-window-item v-for="sidebarTab in tabs" :key="sidebarTab.value" :value="sidebarTab.value">
      <slot :name="sidebarTab.value" />
    </v-tabs-window-item>
  </v-tabs-window>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'

  export interface SidebarTab {
    value: string
    icon: string
    label: string
    disabled?: boolean
  }

  const props = defineProps<{
    tabs: SidebarTab[]
  }>()

  const tab = ref(props.tabs[0]?.value)
</script>
