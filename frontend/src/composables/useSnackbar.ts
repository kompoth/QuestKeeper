import { ref } from 'vue'

export function useSnackbar () {
  const snackbar = ref(false)
  const snackbarText = ref('')
  const snackbarColor = ref('success')

  function notify (text: string, color: string) {
    snackbarText.value = text
    snackbarColor.value = color
    snackbar.value = true
  }

  return { snackbar, snackbarText, snackbarColor, notify }
}
