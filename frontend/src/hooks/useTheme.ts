import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'astrohealth-theme'
const THEME_COLOR: Record<Theme, string> = { light: '#0032A0', dark: '#0032A0' }

function readTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

/** Light is the default. The choice is the user's and is remembered on this device. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[theme])
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // Storage can be unavailable (private mode); the theme still applies for this visit.
    }
  }, [theme])

  const toggle = useCallback(() => setTheme((current) => (current === 'dark' ? 'light' : 'dark')), [])
  return { theme, toggle }
}
