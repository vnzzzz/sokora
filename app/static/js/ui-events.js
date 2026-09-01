/* eslint-env browser */
;(function () {
  'use strict'

  function getEventValue(event) {
    if (!event || !event.detail) return null
    if (event.detail.value !== undefined) return event.detail.value
    return event.detail
  }

  function openModal(event) {
    const modalId = getEventValue(event)
    if (typeof modalId !== 'string' || !modalId) return

    // HX-Trigger は response 受信時に発火するため、beforeend swap の完了後まで1tick待つ。
    window.setTimeout(() => {
      const modal = document.getElementById(modalId)
      if (modal && typeof modal.showModal === 'function' && !modal.open) {
        modal.showModal()
      }
    }, 0)
  }

  function closeModal(event) {
    const modalId = getEventValue(event)
    if (typeof modalId !== 'string' || !modalId) return

    const modal = document.getElementById(modalId)
    if (modal && typeof modal.close === 'function' && modal.open) {
      modal.close()
    }
  }

  function refreshPage() {
    // modal の empty response swap を完了させてから再読込する。
    window.setTimeout(() => window.location.reload(), 50)
  }

  function showMessage(event) {
    const value = getEventValue(event)
    const message = typeof value === 'string' ? value : value && value.message
    if (!message) return

    const container = document.getElementById('ui-message-container')
    if (!container) return

    const alert = document.createElement('div')
    alert.className = 'alert shadow-lg text-sm'
    alert.setAttribute('role', 'status')
    alert.textContent = message
    container.replaceChildren(alert)

    window.setTimeout(() => {
      if (container.contains(alert)) alert.remove()
    }, 3000)
  }

  document.body.addEventListener('openModal', openModal)
  document.body.addEventListener('closeModal', closeModal)
  document.body.addEventListener('refreshPage', refreshPage)
  document.body.addEventListener('showMessage', showMessage)
})()
