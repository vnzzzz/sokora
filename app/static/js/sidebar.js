/* eslint-env browser */
;(function () {
  'use strict'

  const root = document.documentElement
  const toggle = document.querySelector('[data-sidebar-toggle]')
  if (!toggle) return

  function persistState(value) {
    try {
      window.localStorage.setItem('sidebarOpen', value)
    } catch (_error) {
      // Storageが利用できない環境でも、このdocument内の開閉は維持する。
    }
  }

  toggle.addEventListener('click', () => {
    const isOpen = root.dataset.sidebarOpen !== 'false'
    const nextState = String(!isOpen)
    root.dataset.sidebarOpen = nextState
    persistState(nextState)
  })
})()
