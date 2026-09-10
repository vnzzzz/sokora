/* eslint-env browser */
;(function () {
  'use strict'

  const root = document.documentElement
  const toggle = document.querySelector('[data-sidebar-toggle]')
  const sidebar = document.querySelector('.sidebar-panel')
  if (!toggle || !sidebar) return

  let animationTimer = null

  function persistState(value) {
    try {
      window.localStorage.setItem('sidebarOpen', value)
    } catch (_error) {
      // Storageが利用できない環境でも、このdocument内の開閉は維持する。
    }
  }

  function scheduleAnimationCleanup() {
    if (animationTimer !== null) window.clearTimeout(animationTimer)
    animationTimer = window.setTimeout(() => {
      root.classList.remove('sidebar-animating')
      animationTimer = null
    }, 350)
  }

  toggle.addEventListener('click', () => {
    const isOpen = root.dataset.sidebarOpen !== 'false'
    const nextState = String(!isOpen)

    root.classList.add('sidebar-animating')
    // transitionを有効にした初期geometryを確定してからstateを切り替える。
    void sidebar.offsetWidth

    root.dataset.sidebarOpen = nextState
    persistState(nextState)
    scheduleAnimationCleanup()
  })
})()
