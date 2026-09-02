;(function () {
  'use strict'

  if (window.htmx) {
    window.htmx.config.historyCacheSize = 0
  }

  document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle')
    if (themeToggle) {
      const savedTheme = localStorage.getItem('theme') || 'light'

      document.documentElement.setAttribute('data-theme', savedTheme)
      document.body.setAttribute('data-theme', savedTheme)
      themeToggle.checked = savedTheme === 'dark'

      themeToggle.addEventListener('change', function () {
        const newTheme = this.checked ? 'dark' : 'light'
        document.documentElement.setAttribute('data-theme', newTheme)
        document.body.setAttribute('data-theme', newTheme)
        localStorage.setItem('theme', newTheme)
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }))
      })
    }

    function highlightActiveSidebarLink() {
      const currentPath = window.location.pathname
      const menuLinks = document.querySelectorAll('aside a')

      menuLinks.forEach((link) => {
        const linkPath = link.getAttribute('href')
        link.classList.remove('bg-base-300', 'font-medium')
        link.classList.add('btn-ghost')

        if (currentPath === linkPath) {
          link.classList.add('bg-base-300', 'font-medium')
          link.classList.remove('btn-ghost')
          return
        }

        if (linkPath !== '/' && currentPath.startsWith(`${linkPath}/`)) {
          link.classList.add('bg-base-300', 'font-medium')
          link.classList.remove('btn-ghost')
        }
      })
    }

    highlightActiveSidebarLink()
    document.body.addEventListener('htmx:navigated', highlightActiveSidebarLink)
  })
})()
