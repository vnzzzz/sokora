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

document.addEventListener('htmx:responseError', fallbackToFullNavigation)
document.addEventListener('htmx:sendError', fallbackToFullNavigation)
