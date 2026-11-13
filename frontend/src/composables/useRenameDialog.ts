import { ref } from 'vue'

const open = ref(false)
const title = ref('')

let resolveRename: ((title: string | undefined) => void) | undefined

export function useRenameDialog () {
  function openRenameDialog (currentTitle: string): Promise<string | undefined> {
    title.value = currentTitle
    open.value = true
    return new Promise(resolve => {
      resolveRename = resolve
    })
  }

  function confirmRename () {
    open.value = false
    resolveRename?.(title.value)
  }

  function cancelRename () {
    open.value = false
    resolveRename?.(undefined)
  }

  return { renameDialogOpen: open, renameDialogTitle: title, openRenameDialog, confirmRename, cancelRename }
}
