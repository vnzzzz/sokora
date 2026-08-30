;(function () {
  'use strict'

  let serverTodayDate = null
  let cachedTodayDate = null

  function getTodayDate() {
    if (cachedTodayDate) {
      return cachedTodayDate
    }
    // serverTodayDate は init 関数などで設定
    if (serverTodayDate) {
      cachedTodayDate = serverTodayDate
    } else {
      // フォールバックとしてクライアントの現在日付を使用
      const today = new Date()
      const year = today.getFullYear()
      const month = String(today.getMonth() + 1).padStart(2, '0')
      const day = String(today.getDate()).padStart(2, '0')
      cachedTodayDate = `${year}-${month}-${day}`
    }
    return cachedTodayDate
  }

  function loadDayDetail(date) {
    // HTMXがロードされているか確認 (エラー防止)
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', `/day/${date}`, { target: '#detail-area' })
    } else {
      console.error('htmx is not defined. Cannot load day detail.')
    }
  }

  function highlightSelectedDate(date) {
    if (!date) return

    // 他の日付の選択状態を解除
    document.querySelectorAll('.selected-date, .selected-column').forEach((el) => {
      el.classList.remove('selected-date', 'selected-column')
    })

    // 新しい日付を選択状態にする
    const headerCell = document.querySelector(`th.calendar-cell[data-date="${date}"]`)
    if (headerCell) {
      headerCell.classList.add('selected-date')
      void headerCell.offsetHeight // スタイル再計算を強制
    }

    const dateCells = document.querySelectorAll(`td.calendar-cell[data-date="${date}"]`)
    dateCells.forEach((cell) => {
      cell.classList.add('selected-column')
      void cell.offsetHeight // スタイル再計算を強制
    })

    // 選択した日付をlocalStorageに保存
    localStorage.setItem('selectedDate', date)

    // 詳細情報を読み込む
    loadDayDetail(date)
  }

  function setupCalendarSelection() {
    const savedDate = localStorage.getItem('selectedDate')
    const todayDate = getTodayDate() // ここで serverTodayDate が設定されている必要がある

    // 既存の選択状態をクリア
    document.querySelectorAll('.selected-date, .selected-column').forEach((cell) => {
      cell.classList.remove('selected-date', 'selected-column')
    })

    let targetDate = null
    let targetCell = null

    // 保存された日付が存在し、カレンダー上に表示されているか確認
    if (savedDate) {
      targetCell = document.querySelector(`th.calendar-cell[data-date="${savedDate}"]`)
      if (targetCell) {
        targetDate = savedDate
      }
    }

    // 保存された日付が無効、または存在しない場合、今日の日付を試す
    if (!targetCell) {
      targetCell = document.querySelector(`th.calendar-cell[data-date="${todayDate}"]`)
      if (targetCell) {
        targetDate = todayDate
      } else {
        // 今日の日付も表示されていない場合、表示されている最初の日付を選択
        targetCell = document.querySelector('th.calendar-cell[data-date]')
        if (targetCell) {
          targetDate = targetCell.getAttribute('data-date')
        }
      }
    }

    // 選択対象の日付が見つかった場合、ハイライトを実行
    if (targetDate) {
      highlightSelectedDate(targetDate)
      return true
    } else {
      return false
    }
  }

  // クリックイベントハンドラ
  function handleDateClick(event) {
    const date = event.currentTarget.dataset.date
    if (date) {
      highlightSelectedDate(date)
    }
  }

  function initCalendar() {
    const metadataElement = document.getElementById('calendar-metadata')

    if (metadataElement && metadataElement.dataset.todayDate) {
      serverTodayDate = metadataElement.dataset.todayDate
    } else {
      console.warn('Calendar metadata or todayDate not found.')
      // getTodayDateがフォールバックを提供
      serverTodayDate = null // Explicitly set to null so getTodayDate uses client time
    }
    cachedTodayDate = null // キャッシュをリセットして最新の今日日付を使う

    const allCells = document.querySelectorAll('.calendar-cell[data-date]')
    if (allCells.length > 0) {
      // カレンダーの初期選択状態を設定
      setupCalendarSelection()

      // クリックイベントリスナーを設定 (onclick属性の代替)
      allCells.forEach((cell) => {
        cell.removeEventListener('click', handleDateClick) // 念のため既存リスナー削除
        cell.addEventListener('click', handleDateClick)
      })
    } else {
      console.warn('No calendar cells found during init.')
    }
  }

  // --- イベントリスナー設定 ---

  // HTMXでカレンダーコンテナが置き換えられた後に初期化を実行
  document.body.addEventListener('htmx:afterSwap', function (event) {
    // #calendar-area またはその内部要素が更新されたかチェック
    const calendarArea = document.getElementById('calendar-area')
    // event.target が calendarArea の子孫要素であるか、または calendarArea 自身であるかを確認
    if (calendarArea && event.target && calendarArea.contains(event.target)) {
      // #calendar-metadata が存在するか (つまり summary_calendar.html がロードされたか) 確認
      // htmx:afterSwap はスワップされた要素 (event.target) だけでなく、
      // その親要素も含む可能性があるため、document全体で検索する方が確実な場合がある
      if (document.getElementById('calendar-metadata')) {
        setTimeout(initCalendar, 50)
      }
    }
  })

  // ページ初期ロード時にもカレンダーが存在すれば初期化を実行
  function attemptInitialCalendarInit() {
    // #calendar-metadata が DOM に存在するかどうかで summary_calendar がロードされたかを判断
    if (document.getElementById('calendar-metadata')) {
      setTimeout(initCalendar, 50)

      // 選択されていた月があるか確認し、初期表示に反映
      setTimeout(() => {
        const urlParams = new URLSearchParams(window.location.search)
        const monthInUrl = urlParams.get('month')
        // URLに月指定がなければ、localStorageの月情報を使用
        if (!monthInUrl && window.location.pathname.includes('/attendance')) {
          const savedMonth = localStorage.getItem('selectedMonth')
          if (savedMonth) {
            // 保存された月のカレンダーを表示（ページの再読み込みなしで可能かチェック）
            const currentMonthDisplay = document.querySelector('.current-month-display')
            if (currentMonthDisplay && !currentMonthDisplay.textContent.includes(savedMonth)) {
              // 同一ページ内で月切り替えを行う
              if (typeof htmx !== 'undefined') {
                const calendarElement = document.getElementById('calendar')
                if (calendarElement) {
                  const url = `/attendance?month=${encodeURIComponent(savedMonth)}`
                  htmx.ajax('GET', url, { target: '#calendar', swap: 'outerHTML' })
                }
              }
            }
          }
        }
      }, 100)
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attemptInitialCalendarInit)
  } else {
    // DOMがすでに読み込まれている場合
    attemptInitialCalendarInit()
  }

  /**
   * 指定された月のカレンダーページに遷移する
   * @param {string} month - YYYY-MM形式の月、空文字の場合は現在の月
   * @param {string|null} userId - ユーザーID（指定された場合）
   * @param {string} urlBase - 基本URL
   */
  function navigateToMonth(month, userId, urlBase = '/attendance') {
    // 月情報をlocalStorageに保存
    if (month) {
      localStorage.setItem('selectedMonth', month)
    } else {
      localStorage.removeItem('selectedMonth')
    }

    // URLを構築
    let url
    if (userId) {
      url = `${urlBase}/${userId}${month ? `?month=${month}` : ''}`
    } else {
      url = `${urlBase}${month ? `?month=${month}` : ''}`
    }

    // ページ遷移
    window.location.href = url
  }
})()
