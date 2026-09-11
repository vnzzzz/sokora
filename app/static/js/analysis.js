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
    if (!(trigger instanceof HTMLButtonElement)) return

    const isSelected = trigger.dataset.analysisDay === day
    trigger.toggleAttribute('aria-current', isSelected)
    trigger.classList.toggle('text-primary', isSelected)
    trigger.classList.toggle('font-semibold', isSelected)
    trigger.classList.toggle('text-base-content/45', !isSelected)
  })
}

function loadAnalysisDayDetail(trigger) {
  const day = trigger.dataset.analysisDay
  const target = document.querySelector('#analysis-day-detail')
  if (!day || !(target instanceof HTMLElement) || !window.htmx) return

  markSelectedAnalysisDay(day)
  window.htmx.ajax('GET', `/calendar/day/${encodeURIComponent(day)}`, {
    target: '#analysis-day-detail',
    swap: 'innerHTML',
  })
}

document.addEventListener('click', (event) => {
  const target = event.target
  if (!(target instanceof Element)) return

  const dayTrigger = target.closest('[data-analysis-day]')
  if (dayTrigger instanceof HTMLButtonElement) {
    loadAnalysisDayDetail(dayTrigger)
    return
  }

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

document.addEventListener('htmx:responseError', fallbackToFullNavigation)
document.addEventListener('htmx:sendError', fallbackToFullNavigation)
