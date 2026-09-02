/* eslint-env browser */
;(function () {
  'use strict'

  const closingModalIds = new Set()
  const flashMessageKey = 'sokora:ui-message'
  let reloadPending = false
  let latestMessage = null

  function getEventValue(event) {
    if (!event || !event.detail) return null
    if (event.detail.value !== undefined) return event.detail.value
    return event.detail
  }

  function showModal(modalId) {
    const modal = document.getElementById(modalId)
    if (modal && typeof modal.showModal === 'function' && !modal.open) {
      modal.showModal()
    }
  }

  function openModal(event) {
    const modalId = getEventValue(event)
    if (typeof modalId !== 'string' || !modalId) return

    // HX-Trigger は response 受信時に発火するため、beforeend swap の完了後まで1tick待つ。
    window.setTimeout(() => showModal(modalId), 0)
  }

  function closeModal(event) {
    const modalId = getEventValue(event)
    if (typeof modalId !== 'string' || !modalId) return

    closingModalIds.add(modalId)
    window.setTimeout(() => closingModalIds.delete(modalId), 1000)

    const modal = document.getElementById(modalId)
    if (modal && typeof modal.close === 'function' && modal.open) {
      modal.close()
    }
  }

  function storeFlashMessage(message) {
    try {
      window.sessionStorage.setItem(flashMessageKey, message)
    } catch (_error) {
      // Storageが利用できない環境では、その場での表示だけを維持する。
    }
  }

  function takeFlashMessage() {
    try {
      const message = window.sessionStorage.getItem(flashMessageKey)
      if (message) window.sessionStorage.removeItem(flashMessageKey)
      return message
    } catch (_error) {
      return null
    }
  }

  function renderMessage(message) {
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

  function refreshPage() {
    reloadPending = true
    if (latestMessage) storeFlashMessage(latestMessage)
    window.setTimeout(() => window.location.reload(), 50)
  }

  function showMessage(event) {
    const value = getEventValue(event)
    const message = typeof value === 'string' ? value : value && value.message
    if (!message) return

    latestMessage = message
    if (reloadPending) storeFlashMessage(message)
    renderMessage(message)

    // 同じHX-Trigger処理中のrefreshPageだけがこのmessageを引き継げるよう、次tickで破棄する。
    window.setTimeout(() => {
      if (latestMessage === message) latestMessage = null
    }, 0)
  }

  function reopenReplacedModal(event) {
    const target = event.detail && event.detail.target ? event.detail.target : event.target
    if (!target || target.tagName !== 'DIALOG' || !target.id) return
    if (closingModalIds.has(target.id)) return

    window.setTimeout(() => showModal(target.id), 0)
  }

  document.body.addEventListener('openModal', openModal)
  document.body.addEventListener('closeModal', closeModal)
  document.body.addEventListener('refreshPage', refreshPage)
  document.body.addEventListener('showMessage', showMessage)
  document.body.addEventListener('htmx:afterSwap', reopenReplacedModal)

  const flashMessage = takeFlashMessage()
  if (flashMessage) renderMessage(flashMessage)
})()
