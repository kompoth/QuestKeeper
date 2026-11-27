import { ref } from 'vue'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
}

const open = ref(false)
const title = ref('')
const message = ref('')
const confirmText = ref('Confirm')
const cancelText = ref('Cancel')

let resolveConfirm: ((confirmed: boolean) => void) | undefined

// Singleton, same pattern as useRenameDialog - one dialog instance (mounted once, in App.vue),
// triggered from anywhere by awaiting confirmDialog().
export function useConfirmDialog () {
  function confirmDialog (options: ConfirmOptions): Promise<boolean> {
    title.value = options.title ?? 'Confirm'
    message.value = options.message
    confirmText.value = options.confirmText ?? 'Confirm'
    cancelText.value = options.cancelText ?? 'Cancel'
    open.value = true
    return new Promise(resolve => {
      resolveConfirm = resolve
    })
  }

  function acceptConfirm () {
    open.value = false
    resolveConfirm?.(true)
  }

  function rejectConfirm () {
    open.value = false
    resolveConfirm?.(false)
  }

  return {
    confirmDialogOpen: open,
    confirmDialogTitle: title,
    confirmDialogMessage: message,
    confirmDialogConfirmText: confirmText,
    confirmDialogCancelText: cancelText,
    confirmDialog,
    acceptConfirm,
    rejectConfirm,
  }
}
