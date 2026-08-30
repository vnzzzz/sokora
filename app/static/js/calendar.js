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

      // スタイルデータが正しく設定されているか確認（デバッグ用）
      try {
        const stylesElement = document.getElementById('location-styles-data')
        if (stylesElement) {
          const stylesData = stylesElement.dataset.styles
          console.debug('スタイルデータ読み込み:', stylesData ? `データあり(${stylesData.length}文字)` : 'データなし')
        } else {
          console.debug('スタイルデータ要素なし')
        }
      } catch (error) {
        console.error('スタイルデータ確認エラー:', error)
      }

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
      // UI要素を一時的に無効化
      cell.classList.add('animate-pulse')
      const formData = new FormData()
      formData.append('user_id', userId)
      formData.append('date', date)
      formData.append('location_id', locationId)

      fetch('/api/attendances/', {
        method: 'POST',
        body: formData
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`サーバーエラー (${response.status}): ${response.statusText}`)
          }
          return response.json().catch(() => {
            throw new Error('レスポンスの形式が不正です')
          })
        })
        .then((data) => {
          if (!data.success) {
            throw new Error(data.message || '不明なエラーが発生しました')
          }

          // 即時フィードバック用のUI更新はコメントアウト
          // UI更新（即時フィードバック）
          // cell.classList.remove('animate-pulse')
          // cell.dataset.isSelected = 'true'
          //
          // // 勤務場所スタイルを適用
          // try {
          //   const locationStyles = window.calendarHandlers.getLocationStyles()
          //   if (locationStyles[locationType]) {
          //     const styleClasses = locationStyles[locationType].split(' ')
          //     styleClasses.forEach((cls) => cell.classList.add(cls))
          //   }
          //
          //   // マーカーを追加
          //   const marker = document.createElement('div')
          //   marker.className = 'text-sm location-marker'
          //   marker.textContent = '●'
          //   cell.appendChild(marker)
          // } catch (styleError) {
          //   console.error('スタイル適用エラー:', styleError)
          // }

          // HTMXを使用してカレンダー部分だけを更新
          window.calendarHandlers.refreshCalendarContent(userId)

          return data
        })
        .catch((error) => {
          // エラー時もUI状態を元に戻す
          cell.classList.remove('animate-pulse')
          console.error('勤怠登録エラー:', error)
          alert('予定の登録に失敗しました: ' + error.message)
        })
    },

    // 勤怠削除処理
    deleteAttendance: function (date, userId, cell) {
      // UI要素を一時的に無効化
      cell.classList.add('animate-pulse')

      // 対象日の予定IDを取得
      fetch(`/api/attendances/user/${userId}?date=${date}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`サーバーエラー (${response.status}): ${response.statusText}`)
          }
          return response.json().catch(() => {
            throw new Error('レスポンスの形式が不正です')
          })
        })
        .then((data) => {
          // データがない場合は処理終了
          if (!data || !data.dates || data.dates.length === 0) {
            // UI状態を復元して終了
            cell.classList.remove('animate-pulse')
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
            throw new Error(`サーバーエラー (${response.status}): ${response.statusText}`)
          }

          return response.json().catch(() => {
            throw new Error('レスポンスの形式が不正です')
          })
        })
        .then((data) => {
          if (!data) {
            return // 前のthenで既に処理終了している場合
          }

          if (!data.success) {
            throw new Error(data.message || '不明なエラーが発生しました')
          }

          // 即時フィードバック用のUI更新はコメントアウト
          // // UI更新（即時フィードバック）
          // cell.classList.remove('animate-pulse')
          // cell.dataset.isSelected = 'false'
          //
          // // スタイルクラスを削除
          // const styleClasses = cell.className
          //   .split(' ')
          //   .filter((cls) => cls.startsWith('bg-') || cls.startsWith('text-'))
          // styleClasses.forEach((cls) => cell.classList.remove(cls))
          //
          // // マーカーを削除
          // const marker = cell.querySelector('.location-marker')
          // if (marker) marker.remove()

          // HTMXを使用してカレンダー部分だけを更新
          window.calendarHandlers.refreshCalendarContent(userId)
        })
        .catch((error) => {
          // エラー時もUI状態を元に戻す
          cell.classList.remove('animate-pulse')
          console.error('勤怠削除エラー:', error)
          alert('予定の削除に失敗しました: ' + error.message)
        })
    },

    // カレンダー部分だけを更新する関数
    refreshCalendarContent: function (userId) {
      const container = document.getElementById('attendance-edit-container')
      if (!container) {
        console.error('カレンダーコンテナが見つかりません')
        return
      }

      // すべてのセルのアニメーションをリセット
      document.querySelectorAll('.calendar-cell').forEach((cell) => {
        cell.classList.remove('animate-pulse')
      })

      // 現在の月を取得（URLから）
      const urlParams = new URLSearchParams(window.location.search)
      const month = urlParams.get('month') || ''

      // コンテナにローディング表示
      container.classList.add('opacity-60')

      // カレンダー部分だけを再取得
      fetch(`/attendance/edit/${userId}?month=${month}`, {
        headers: {
          'HX-Request': 'true' // HTMXリクエストをシミュレート
        }
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error('カレンダーデータの取得に失敗しました')
          }
          return response.text()
        })
        .then((html) => {
          // カレンダー部分を更新
          container.innerHTML = html
          container.classList.remove('opacity-60')

          // カレンダーの初期化処理を呼び出し
          setTimeout(() => {
            window.calendarHandlers.initCalendarCells()
          }, 50)
        })
        .catch((error) => {
          console.error('カレンダー更新エラー:', error)
          container.classList.remove('opacity-60')
          // エラーが発生した場合に備えてプレースホルダを表示
          container.innerHTML += `<div class="alert alert-error shadow-lg mt-4">
          <div>
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>更新エラー: ${error.message}。ページをリロードしてください。</span>
          </div>
        </div>`
        })
    },

    // スタイル取得
    getLocationStyles: function () {
      try {
        // DOM要素の存在確認
        const stylesElement = document.getElementById('location-styles-data')
        if (!stylesElement) {
          console.warn('勤務場所スタイルデータが見つかりません')
          return {}
        }

        // データ属性の値を取得
        const stylesData = stylesElement.dataset.styles
        if (!stylesData || stylesData.trim() === '') {
          console.warn('勤務場所スタイルデータが空です')
          return {}
        }

        // デバッグ出力
        // console.log('スタイルデータ:', stylesData)

        // JSONパース（エラーハンドリング付き）
        try {
          return JSON.parse(stylesData)
        } catch (parseError) {
          console.error('勤務場所スタイルデータのJSONパースエラー:', parseError, stylesData)
          return {}
        }
      } catch (error) {
        console.error('勤務場所スタイル取得エラー:', error)
        return {}
      }
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
