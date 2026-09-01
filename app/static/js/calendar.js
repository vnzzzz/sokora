;(function () {
  'use strict'

  let serverTodayDate = null
  let cachedTodayDate = null

  function getTodayDate() {
    if (cachedTodayDate) return cachedTodayDate

    if (serverTodayDate) {
      cachedTodayDate = serverTodayDate
      return cachedTodayDate
    }

    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    cachedTodayDate = `${year}-${month}-${day}`
    return cachedTodayDate
  }

  function loadDayDetail(date) {
    if (!window.htmx) return
    window.htmx.ajax('GET', `/calendar/day/${date}`, { target: '#detail-area' })
  }

  function highlightSelectedDate(date) {
    if (!date) return

    document.querySelectorAll('.selected-date, .selected-column').forEach((element) => {
      element.classList.remove('selected-date', 'selected-column')
    })

    const headerCell = document.querySelector(`th.calendar-cell[data-date="${date}"]`)
    if (headerCell) headerCell.classList.add('selected-date')

    document.querySelectorAll(`td.calendar-cell[data-date="${date}"]`).forEach((cell) => {
      cell.classList.add('selected-column')
    })

    localStorage.setItem('selectedDate', date)
    loadDayDetail(date)
  }

  function setupCalendarSelection() {
    const todayDate = getTodayDate()
    const todayCell = document.querySelector(`th.calendar-cell[data-date="${todayDate}"]`)
    const firstCell = document.querySelector('th.calendar-cell[data-date]')
    const target = todayCell || firstCell

    if (target) highlightSelectedDate(target.dataset.date)
  }

  function handleDateClick(event) {
    highlightSelectedDate(event.currentTarget.dataset.date)
  }

  function initCalendar() {
    const metadata = document.getElementById('calendar-metadata')
    serverTodayDate = metadata && metadata.dataset.todayDate ? metadata.dataset.todayDate : null
    cachedTodayDate = null

    const cells = document.querySelectorAll('.calendar-cell[data-date]')
    if (!cells.length) return

    setupCalendarSelection()
    cells.forEach((cell) => {
      cell.removeEventListener('click', handleDateClick)
      cell.addEventListener('click', handleDateClick)
    })
  }

  document.body.addEventListener('htmx:afterSwap', (event) => {
    const calendarArea = document.getElementById('calendar-area')
    if (
      calendarArea &&
      event.target &&
      calendarArea.contains(event.target) &&
      document.getElementById('calendar-metadata')
    ) {
      window.setTimeout(initCalendar, 50)
    }
  })

  function initializeIfPresent() {
    if (document.getElementById('calendar-metadata')) {
      window.setTimeout(initCalendar, 50)
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeIfPresent)
  } else {
    initializeIfPresent()
  }
})()
