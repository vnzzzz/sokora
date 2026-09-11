/**
 * analysis pageでHTMXだけでは表現しにくい最小限のbrowser behavior。
 */

function analysisFallbackUrl(element) {
  if (!(element instanceof Element) || !element.closest('#analysis-view')) return null

  const modeTab = element.closest('[data-analysis-mode-tab]')
  if (modeTab instanceof HTMLAnchorElement) {
    return modeTab.getAttribute('href')
  }

  if (element.id === 'month-input') {
    return element.value ? `/analysis?month=${encodeURIComponent(element.value)}` : '/analysis'
  }

  if (element.id === 'year-select') {
    return element.value
      ? `/analysis?mode=year&year=${encodeURIComponent(element.value)}`
      : '/analysis?mode=year'
  }

  if (element.closest('#analysis-location-filter')) {
    return window.location.href
  }

  return null
}

function fallbackToFullNavigation(event) {
  const url = analysisFallbackUrl(event.detail?.elt)
  if (url) window.location.href = url
}

function setAllAnalysisSeries(button, checked) {
  const form = button.closest('#analysis-location-filter')
  if (!(form instanceof HTMLFormElement)) return

  form.querySelectorAll('[data-analysis-series-checkbox]').forEach((checkbox) => {
    if (checkbox instanceof HTMLInputElement) checkbox.checked = checked
  })
  form.dispatchEvent(new Event('change', { bubbles: true }))
}

function markSelectedAnalysisDay(day) {
  document.querySelectorAll('[data-analysis-day]').forEach((trigger) => {
    if (!(trigger instanceof Element)) return

    const isSelected = trigger.getAttribute('data-analysis-day') === day
    if (isSelected) trigger.setAttribute('aria-current', 'date')
    else trigger.removeAttribute('aria-current')
    trigger.classList.toggle('text-primary', isSelected)
    trigger.classList.toggle('font-semibold', isSelected)
    trigger.classList.toggle('text-base-content/45', !isSelected)
  })
}

function loadAnalysisDayDetail(trigger) {
  const day = trigger.getAttribute('data-analysis-day')
  const target = document.querySelector('#analysis-day-detail')
  if (!day || !(target instanceof HTMLElement)) return

  markSelectedAnalysisDay(day)
  target.setAttribute('aria-busy', 'true')

  if (!window.htmx) {
    window.location.href = `/calendar/day/${encodeURIComponent(day)}`
    return
  }

  window.htmx.ajax('GET', `/calendar/day/${encodeURIComponent(day)}`, {
    target: '#analysis-day-detail',
    swap: 'innerHTML',
  })
}

function activateAnalysisDayTrigger(trigger) {
  if (!(trigger instanceof Element)) return false
  loadAnalysisDayDetail(trigger)
  return true
}

document.addEventListener('click', (event) => {
  const target = event.target
  if (!(target instanceof Element)) return

  const dayTrigger = target.closest('[data-analysis-day]')
  if (activateAnalysisDayTrigger(dayTrigger)) return

  const selectAllButton = target.closest('[data-analysis-select-all]')
  if (selectAllButton instanceof HTMLButtonElement) {
    setAllAnalysisSeries(selectAllButton, true)
    return
  }

  const clearAllButton = target.closest('[data-analysis-clear-all]')
  if (clearAllButton instanceof HTMLButtonElement) {
    setAllAnalysisSeries(clearAllButton, false)
  }
})

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' && event.key !== ' ') return

  const target = event.target
  if (!(target instanceof Element)) return

  const dayTrigger = target.closest('[data-analysis-day]')
  if (!dayTrigger) return

  event.preventDefault()
  activateAnalysisDayTrigger(dayTrigger)
})

document.addEventListener('htmx:afterSwap', (event) => {
  const target = event.detail?.target
  if (!(target instanceof HTMLElement) || target.id !== 'analysis-day-detail') return

  target.setAttribute('aria-busy', 'false')
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
})

document.addEventListener('htmx:responseError', fallbackToFullNavigation)
document.addEventListener('htmx:sendError', fallbackToFullNavigation)
