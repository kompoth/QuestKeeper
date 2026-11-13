import type { World } from '@/types/world'
import { computed, ref } from 'vue'

export interface WorldFormResult {
  name: string
  description: string
}

const open = ref(false)
const editingWorld = ref<World | undefined>(undefined)
const name = ref('')
const description = ref('')

let resolveWorldForm: ((result: WorldFormResult | undefined) => void) | undefined

export function useWorldFormDialog () {
  const isEdit = computed(() => editingWorld.value !== undefined)

  function openWorldFormDialog (world?: World): Promise<WorldFormResult | undefined> {
    editingWorld.value = world
    name.value = world?.name ?? ''
    description.value = world?.description ?? ''
    open.value = true
    return new Promise(resolve => {
      resolveWorldForm = resolve
    })
  }

  function confirmWorldForm () {
    open.value = false
    resolveWorldForm?.({ name: name.value, description: description.value })
  }

  function cancelWorldForm () {
    open.value = false
    resolveWorldForm?.(undefined)
  }

  return {
    worldFormOpen: open,
    worldFormName: name,
    worldFormDescription: description,
    worldFormIsEdit: isEdit,
    openWorldFormDialog,
    confirmWorldForm,
    cancelWorldForm,
  }
}
