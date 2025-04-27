// カレンダー関連の共通JavaScript処理

// グローバルスコープで一度だけ初期化する部分
if (typeof window.calendarHandlers === 'undefined') {
  // カレンダー関連の関数をグローバルに一度だけ定義
  window.calendarHandlers = {
    initialized: false,

    // デバッグ情報の表示
    logDebugInfo: function () {
      const debugEl = document.getElementById('calendar-debug-info')
      if (debugEl) {
        const monthName = debugEl.dataset.monthName || ''
        const prevMonth = debugEl.dataset.prevMonth || ''
        const nextMonth = debugEl.dataset.nextMonth || ''
        const userId = debugEl.dataset.userId || ''
        const userDatesCount = debugEl.dataset.userDatesCount || '0'
      }
    },

    // カレンダーセルの初期化
    initCalendarCells: function () {
      // デバッグ情報を表示
      this.logDebugInfo()

      // カレンダーセルにクリックイベントを追加
      const cells = document.querySelectorAll('.calendar-cell')
      if (cells.length === 0) {
        setTimeout(window.calendarHandlers.initCalendarCells, 1000)
        return
      }

      cells.forEach((cell) => {
        // 既存のイベントリスナを削除してから追加（重複防止）
        cell.removeEventListener('click', window.calendarHandlers.handleCellClick)
        cell.addEventListener('click', window.calendarHandlers.handleCellClick)
      })

      // 今日の日付をハイライト
      window.calendarHandlers.highlightToday()

      window.calendarHandlers.initialized = true
    },

    // セルクリック時の処理
    handleCellClick: function (event) {
      const cell = event.currentTarget
      const date = cell.dataset.date
      const locationId = cell.dataset.locationId
      const locationType = cell.dataset.locationType
      const userId = cell.dataset.userId
      const isSelected = cell.dataset.isSelected === 'true'

      // 同じ日付の他のセルを選択解除
      if (!isSelected) {
        document.querySelectorAll(`.calendar-cell[data-date="${date}"]`).forEach((otherCell) => {
          if (otherCell.dataset.isSelected === 'true') {
            otherCell.dataset.isSelected = 'false'
            // スタイルクラスを削除
            const styleClasses = otherCell.className
              .split(' ')
              .filter((cls) => cls.startsWith('bg-') || cls.startsWith('text-'))
            styleClasses.forEach((cls) => otherCell.classList.remove(cls))
            // マーカーを削除
            const marker = otherCell.querySelector('.location-marker')
            if (marker) marker.remove()
          }
        })
      }

      if (isSelected) {
        // 選択解除して予定を削除
        window.calendarHandlers.deleteAttendance(date, userId, cell)
      } else {
        // 選択して予定を追加
        window.calendarHandlers.createAttendance(date, userId, locationId, cell, locationType)
      }
    },

    // 勤怠登録処理
    createAttendance: function (date, userId, locationId, cell, locationType) {
      const formData = new FormData()
      formData.append('user_id', userId)
      formData.append('date', date)
      formData.append('location_id', locationId)

      fetch('/api/attendances/', {
        method: 'POST',
        body: formData
      })
        .then((response) => {
          if (response.ok) {
            // UI更新
            cell.dataset.isSelected = 'true'

            // 勤務場所スタイルを適用
            const locationStyles = window.calendarHandlers.getLocationStyles()
            if (locationStyles[locationType]) {
              const styleClasses = locationStyles[locationType].split(' ')
              styleClasses.forEach((cls) => cell.classList.add(cls))
            }

            // マーカーを追加
            const marker = document.createElement('div')
            marker.className = 'text-sm location-marker'
            marker.textContent = '●'
            cell.appendChild(marker)

            return response.json()
          } else {
            throw new Error('登録に失敗しました')
          }
        })
        .catch((error) => {
          alert('予定の登録に失敗しました: ' + error.message)
        })
    },

    // 勤怠削除処理
    deleteAttendance: function (date, userId, cell) {
      // 対象日の予定IDを取得
      fetch(`/api/attendances/user/${userId}?date=${date}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error('予定データの取得に失敗しました')
          }
          return response.json()
        })
        .then((data) => {
          // データがない場合は処理終了
          if (!data || !data.dates || data.dates.length === 0) {
            return null
          }

          // 予定IDを取得
          const attendanceId = data.dates[0].attendance_id
          if (!attendanceId) {
            throw new Error('予定IDが見つかりませんでした')
          }

          // 予定を削除
          return fetch(`/api/attendances/${attendanceId}`, {
            method: 'DELETE'
          })
        })
        .then((response) => {
          if (!response) {
            return
          }

          if (!response.ok) {
            throw new Error('削除リクエストが失敗しました')
          }

          // UI更新
          cell.dataset.isSelected = 'false'

          // スタイルクラスを削除
          const styleClasses = cell.className
            .split(' ')
            .filter((cls) => cls.startsWith('bg-') || cls.startsWith('text-'))
          styleClasses.forEach((cls) => cell.classList.remove(cls))

          // マーカーを削除
          const marker = cell.querySelector('.location-marker')
          if (marker) marker.remove()
        })
        .catch((error) => {
          alert('予定の削除に失敗しました: ' + error.message)
        })
    },

    // スタイル取得
    getLocationStyles: function () {
      // この関数はサーバーから提供された location_styles を返します
      return JSON.parse(document.getElementById('location-styles-data').dataset.styles || '{}')
    },

    // 今日の日付ハイライト
    highlightToday: function () {
      const today = new Date()
      const year = today.getFullYear()
      const month = String(today.getMonth() + 1).padStart(2, '0')
      const day = String(today.getDate()).padStart(2, '0')
      const todayDate = `${year}-${month}-${day}`

      // 今日の日付のヘッダーを強調
      const todayHeader = document.querySelector(`.calendar-header-cell[data-date="${todayDate}"]`)
      if (todayHeader) {
        todayHeader.classList.add('today-highlight', 'border-gray-500', 'border-2')
      }
    }
  }

  // グローバルイベントリスナーの設定（一度だけ）
  document.body.addEventListener('htmx:afterSwap', function (event) {
    // カレンダーコンテナが更新された場合、または
    // bodyが更新された場合（月切り替え時）に初期化
    if (
      event.detail.target.id === 'calendar-container' ||
      event.detail.target.id === 'attendance-edit-container' ||
      event.detail.target.id === 'day-detail-container' ||
      event.detail.target === document.body
    ) {
      // 確実に初期化されるよう少し遅延させて実行
      setTimeout(window.calendarHandlers.initCalendarCells, 100)
    }
  })
}

// 月切り替え処理
function navigateToMonth(month, userId, baseUrl) {
  if (!baseUrl) {
    // 標準のURLを設定
    if (userId) {
      baseUrl = `/attendance/edit/${userId}`
    } else {
      baseUrl = window.location.pathname
    }
  }

  const url = month ? `${baseUrl}?month=${month}` : baseUrl

  // ページ全体をリロードして移動
  window.location.href = url
}

// ページロード時に初期化
document.addEventListener('DOMContentLoaded', function () {
  window.calendarHandlers.initCalendarCells()
})

// HTMXによるコンテンツ置換直後も初期化を呼び出す
if (document.readyState === 'complete') {
  // すでにDOMがロードされている場合は直接初期化
  window.calendarHandlers.initCalendarCells()
}
