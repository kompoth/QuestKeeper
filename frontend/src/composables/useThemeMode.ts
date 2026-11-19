import { useTheme } from 'vuetify'

const STORAGE_KEY = 'theme-mode'

type ThemeMode = 'light' | 'dark'

export function useThemeMode () {
  const theme = useTheme()

  function apply (mode: ThemeMode) {
    theme.global.name.value = mode
    document.documentElement.dataset.theme = mode
    localStorage.setItem(STORAGE_KEY, mode)
  }

  function init () {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      apply(stored)
    } else {
      apply(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    }
  }

  function toggle () {
    apply(theme.global.current.value.dark ? 'light' : 'dark')
  }

  return { theme, init, toggle }
}
