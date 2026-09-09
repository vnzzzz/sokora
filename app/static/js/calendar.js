;(function () {
  'use strict'

  const calendarArea = document.getElementById('calendar-area')
  if (!calendarArea) return

  function getTodayDate() {
    const metadata = calendarArea.querySelector('#calendar-metadata')
    if (metadata && metadata.dataset.todayDate) return metadata.dataset.todayDate

    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  function loadDayDetail(date) {
    if (!window.htmx) return
    window.htmx.ajax('GET', `/calendar/day/${date}`, { target: '#detail-area' })
  }

  function highlightSelectedDate(date) {
    if (!date) return

    calendarArea.querySelectorAll('.selected-date, .selected-column').forEach((element) => {
      element.classList.remove('selected-date', 'selected-column')
    })

    const headerCell = calendarArea.querySelector(`th.calendar-cell[data-date="${date}"]`)
    if (headerCell) headerCell.classList.add('selected-date')

    calendarArea.querySelectorAll(`td.calendar-cell[data-date="${date}"]`).forEach((cell) => {
      cell.classList.add('selected-column')
    })

    localStorage.setItem('selectedDate', date)
    loadDayDetail(date)
  }

  function initializeCalendar() {
    if (!calendarArea.querySelector('#calendar-metadata')) return

    const todayDate = getTodayDate()
    const target =
      calendarArea.querySelector(`th.calendar-cell[data-date="${todayDate}"]`) ||
      calendarArea.querySelector('th.calendar-cell[data-date]')

    if (target) highlightSelectedDate(target.dataset.date)
  }

  calendarArea.addEventListener('click', (event) => {
    const cell = event.target.closest('.calendar-cell[data-date]')
    if (!cell || !calendarArea.contains(cell)) return
    highlightSelectedDate(cell.dataset.date)
  })

  document.body.addEventListener('htmx:afterSwap', (event) => {
    if (event.target === calendarArea || calendarArea.contains(event.target)) {
      initializeCalendar()
    }
  })

  initializeCalendar()
})()
