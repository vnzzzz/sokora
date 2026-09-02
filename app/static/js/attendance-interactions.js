/* eslint-env browser */
/* globals htmx */
;(function () {
  'use strict'

  const MONTH_KEY = 'selectedMonth'
  const WEEK_KEY = 'selectedWeek'
  const DEBOUNCE_MS = 200

  let calendarRefreshTimer = null
  let userCalendarRefreshTimer = null
  let pendingAttendanceRefresh = null
  let attendanceRefreshTimer = null

  function getCurrentMonth() {
    return localStorage.getItem(MONTH_KEY)
  }

  function getCurrentWeek() {
    return localStorage.getItem(WEEK_KEY)
  }

  function saveCurrentMonth(month) {
    if (month) localStorage.setItem(MONTH_KEY, month)
  }

  function saveCurrentWeek(week) {
    if (week) localStorage.setItem(WEEK_KEY, week)
  }

  function savePeriodFromUrl() {
    const params = new URLSearchParams(window.location.search)
    saveCurrentMonth(params.get('month'))
    saveCurrentWeek(params.get('week'))
  }

  function getMonday(dateString) {
    if (!dateString) return null

    const date = new Date(`${dateString}T00:00:00`)
    if (Number.isNaN(date.getTime())) return null

    const day = date.getDay()
    const mondayOffset = day === 0 ? 6 : day - 1
    date.setDate(date.getDate() - mondayOffset)

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const dayOfMonth = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${dayOfMonth}`
  }

  function rememberAttendanceDate(dateString) {
    if (!dateString) return
    saveCurrentMonth(dateString.slice(0, 7))
    saveCurrentWeek(getMonday(dateString))
  }

  function refreshCalendar(month) {
    const resolvedMonth = month || getCurrentMonth()
    if (resolvedMonth) saveCurrentMonth(resolvedMonth)

    window.clearTimeout(calendarRefreshTimer)
    calendarRefreshTimer = window.setTimeout(() => {
      const target = document.getElementById('calendar')
      if (!target) return

      const url = resolvedMonth
        ? `/attendance/monthly?month=${encodeURIComponent(resolvedMonth)}`
        : '/attendance/monthly'
      htmx.ajax('GET', url, { target, swap: 'innerHTML' })
    }, DEBOUNCE_MS)
  }

  function refreshWeekCalendar(week) {
    const resolvedWeek = week || getCurrentWeek()
    if (resolvedWeek) saveCurrentWeek(resolvedWeek)

    window.clearTimeout(calendarRefreshTimer)
    calendarRefreshTimer = window.setTimeout(() => {
      const target = document.getElementById('calendar')
      if (!target) return

      const url = resolvedWeek
        ? `/attendance/weekly?week=${encodeURIComponent(resolvedWeek)}`
        : '/attendance/weekly'
      htmx.ajax('GET', url, { target, swap: 'innerHTML' })
    }, DEBOUNCE_MS)
  }

  function refreshUserCalendar(userId, month) {
    if (!userId || !window.location.pathname.includes('/attendance/monthly')) return

    const resolvedMonth = month || getCurrentMonth()
    if (resolvedMonth) saveCurrentMonth(resolvedMonth)

    window.clearTimeout(userCalendarRefreshTimer)
    userCalendarRefreshTimer = window.setTimeout(() => {
      const target = document.getElementById('user-calendar')
      if (!target) return

      const encodedUserId = encodeURIComponent(userId)
      const url = resolvedMonth
        ? `/attendance/monthly/users/${encodedUserId}?month=${encodeURIComponent(resolvedMonth)}`
        : `/attendance/monthly/users/${encodedUserId}`
      htmx.ajax('GET', url, { target, swap: 'outerHTML' })
    }, DEBOUNCE_MS)
  }

  function eventPayload(event) {
    if (!event || !event.detail) return {}
    if (event.detail.value && typeof event.detail.value === 'object') {
      return event.detail.value
    }
    return event.detail
  }

  function queueAttendanceRefresh(kind, event) {
    const payload = eventPayload(event)

    // 同一responseが refreshUserAttendance と refreshAttendance の両方を送る場合、
    // user情報を持つ前者を優先し、1回の再取得へcoalesceする。
    if (kind === 'user' || !pendingAttendanceRefresh) {
      pendingAttendanceRefresh = { kind, payload }
    }

    window.clearTimeout(attendanceRefreshTimer)
    attendanceRefreshTimer = window.setTimeout(() => {
      const pending = pendingAttendanceRefresh
      pendingAttendanceRefresh = null
      attendanceRefreshTimer = null
      if (!pending) return

      const { payload: data } = pending
      const month = data.month || getCurrentMonth()
      const week = data.week || getCurrentWeek()

      if (month) saveCurrentMonth(month)
      if (week) saveCurrentWeek(week)

      if (window.location.pathname.includes('/attendance/monthly') && pending.kind === 'user') {
        refreshUserCalendar(data.user_id || data.userId, month)
      } else if (window.location.pathname.includes('/attendance/weekly') && week) {
        refreshWeekCalendar(week)
      } else {
        refreshCalendar(month)
      }
    }, 0)
  }

  function initializeAttendanceModals(root) {
    const scope = root && root.querySelectorAll ? root : document
    const modals = []

    if (scope.matches && scope.matches('[data-attendance-modal-date]')) modals.push(scope)
    scope.querySelectorAll('[data-attendance-modal-date]').forEach((modal) => modals.push(modal))

    modals.forEach((modal) => {
      if (modal.dataset.attendanceInitialized === 'true') return
      modal.dataset.attendanceInitialized = 'true'
      rememberAttendanceDate(modal.dataset.attendanceModalDate)
    })
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('.location-select-btn')
    if (!button) return

    const modal = button.closest('dialog')
    if (!modal) return

    modal.querySelectorAll('.location-select-btn').forEach((candidate) => {
      candidate.classList.toggle('btn-active', candidate === button)
    })

    const input = modal.querySelector('input[name="location_id"]')
    if (input) input.value = button.dataset.locationId || ''
  })

  document.body.addEventListener('refreshUserAttendance', (event) => {
    queueAttendanceRefresh('user', event)
  })

  document.body.addEventListener('refreshAttendance', (event) => {
    queueAttendanceRefresh('attendance', event)
  })

  document.body.addEventListener('htmx:beforeRequest', (event) => {
    const element = event.detail && event.detail.elt
    if (!element || element.tagName !== 'BUTTON' || !element.hasAttribute('hx-get')) return

    const url = new URL(element.getAttribute('hx-get'), window.location.origin)
    const month = url.searchParams.get('month')
    const week = url.searchParams.get('week')

    if (month) saveCurrentMonth(month)
    if (week) saveCurrentWeek(week)
    if (!month && element.textContent.trim() === '今月') localStorage.removeItem(MONTH_KEY)
    if (!week && element.textContent.trim() === '今週') localStorage.removeItem(WEEK_KEY)
  })

  document.body.addEventListener('htmx:afterSwap', (event) => {
    initializeAttendanceModals(event.target)
  })

  document.addEventListener('DOMContentLoaded', () => {
    savePeriodFromUrl()
    initializeAttendanceModals(document)

    const params = new URLSearchParams(window.location.search)
    const savedWeek = getCurrentWeek()
    if (
      window.location.pathname.includes('/attendance/weekly') &&
      savedWeek &&
      !params.get('week')
    ) {
      refreshWeekCalendar(savedWeek)
    }
  })
})()
