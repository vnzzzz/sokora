/**
 * Persist and apply the global DaisyUI theme without depending on Alpine.
 */

function normalizeTheme(theme) {
  return theme === 'dark' ? 'dark' : 'light'
}

function readStoredTheme() {
  try {
    return normalizeTheme(localStorage.getItem('theme'))
  } catch (_error) {
    return normalizeTheme(document.documentElement.getAttribute('data-theme'))
  }
}

function applyTheme(theme, { persist = true } = {}) {
  const normalizedTheme = normalizeTheme(theme)
  document.documentElement.setAttribute('data-theme', normalizedTheme)
  if (document.body) document.body.setAttribute('data-theme', normalizedTheme)

  if (persist) {
    try {
      localStorage.setItem('theme', normalizedTheme)
    } catch (_error) {
      // Storage unavailable: keep the theme for the current page only.
    }
  }

  const toggle = document.querySelector('#theme-toggle')
  if (toggle instanceof HTMLInputElement) {
    toggle.checked = normalizedTheme === 'dark'
  }
}

function initializeThemeToggle() {
  const toggle = document.querySelector('#theme-toggle')
  if (!(toggle instanceof HTMLInputElement)) return

  applyTheme(readStoredTheme(), { persist: false })
  toggle.addEventListener('change', () => {
    applyTheme(toggle.checked ? 'dark' : 'light')
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeThemeToggle, { once: true })
} else {
  initializeThemeToggle()
}
