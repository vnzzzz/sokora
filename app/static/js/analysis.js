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

  if (window.htmx) {
    window.htmx.trigger(form, 'analysis:filters-changed')
  } else {
    form.dispatchEvent(new Event('analysis:filters-changed', { bubbles: true }))
  }
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

function analysisDayDetailUrl(day) {
  const params = new URLSearchParams()
  const form = document.querySelector('#analysis-location-filter')

  if (form instanceof HTMLFormElement) {
    const groupSelect = form.querySelector('#analysis-group-select')
    const userTypeSelect = form.querySelector('#analysis-user-type-select')

    if (groupSelect instanceof HTMLSelectElement && groupSelect.value) {
      params.set('group_name', groupSelect.value)
    }
    if (userTypeSelect instanceof HTMLSelectElement && userTypeSelect.value) {
      params.set('user_type_name', userTypeSelect.value)
    }

    form.querySelectorAll('input[name="selected_locations"]:checked').forEach((checkbox) => {
      if (checkbox instanceof HTMLInputElement) {
        params.append('selected_locations', checkbox.value)
      }
    })
  }

  const query = params.toString()
  return `/analysis/day/${encodeURIComponent(day)}${query ? `?${query}` : ''}`
}

let analysisDayDetailRequestId = 0

async function loadAnalysisDayDetail(trigger) {
  const day = trigger.getAttribute('data-analysis-day')
  const target = document.querySelector('#analysis-day-detail')
  if (!day || !(target instanceof HTMLElement)) return

  // 連続clickで先行requestが後着した場合に選択と無関係な日付で上書きしないよう、
  // 発火時点のrequestだけが最新であることをtokenで確認してから反映する。
  const requestId = ++analysisDayDetailRequestId

  markSelectedAnalysisDay(day)
  target.setAttribute('aria-busy', 'true')
  target.innerHTML =
    '<div class="flex min-h-24 items-center justify-center" aria-label="読み込み中"><span class="loading loading-spinner loading-sm"></span></div>'
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })

  try {
    const response = await fetch(analysisDayDetailUrl(day), {
      credentials: 'same-origin',
      headers: { 'HX-Request': 'true' },
    })

    if (requestId !== analysisDayDetailRequestId) return

    if (response.redirected) {
      window.location.href = response.url
      return
    }
    if (!response.ok) throw new Error(`day detail request failed: ${response.status}`)

    const html = await response.text()
    if (requestId !== analysisDayDetailRequestId) return

    target.innerHTML = html
    target.setAttribute('aria-busy', 'false')
    if (window.htmx) window.htmx.process(target)
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (_error) {
    if (requestId !== analysisDayDetailRequestId) return
    target.setAttribute('aria-busy', 'false')
    target.innerHTML =
      '<div class="alert alert-error text-sm" role="alert">勤怠明細を読み込めませんでした。</div>'
  }
}

function activateAnalysisDayTrigger(trigger) {
  if (!(trigger instanceof Element)) return false
  void loadAnalysisDayDetail(trigger)
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

document.addEventListener('htmx:responseError', fallbackToFullNavigation)
document.addEventListener('htmx:sendError', fallbackToFullNavigation)
