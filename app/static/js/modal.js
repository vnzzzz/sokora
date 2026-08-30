/* eslint-env browser */
/* globals htmx */
;(function () {
  'use strict'

  // デバッグモード
  const DEBUG = false

  function log(...args) {
    // ログ出力を削除
  }

  /**
   * 現在表示中の月を取得する
   * @returns {string|null} YYYY-MM形式の月、または取得できない場合はnull
   */
  function getCurrentMonth() {
    // localStorageから取得
    return localStorage.getItem('selectedMonth')
  }

  /**
   * 現在表示中の週を取得する
   * @returns {string|null} YYYY-MM-DD形式の週（月曜日）、または取得できない場合はnull
   */
  function getCurrentWeek() {
    // localStorageから取得
    return localStorage.getItem('selectedWeek')
  }

  /**
   * 表示中の月を保存する
   * @param {string} month - YYYY-MM形式の月
   */
  function saveCurrentMonth(month) {
    if (month) {
      localStorage.setItem('selectedMonth', month)
    }
  }

  /**
   * 表示中の週を保存する
   * @param {string} week - YYYY-MM-DD形式の週（月曜日）
   */
  function saveCurrentWeek(week) {
    if (week) {
      localStorage.setItem('selectedWeek', week)
    }
  }

  /**
   * URLから月情報を抽出して保存
   */
  function saveMonthFromUrl() {
    const urlParams = new URLSearchParams(window.location.search)
    const monthParam = urlParams.get('month')
    if (monthParam) {
      saveCurrentMonth(monthParam)
    }
  }

  /**
   * URLから週情報を抽出して保存
   */
  function saveWeekFromUrl() {
    const urlParams = new URLSearchParams(window.location.search)
    const weekParam = urlParams.get('week')
    if (weekParam) {
      saveCurrentWeek(weekParam)
    }
  }

  /**
   * 日付から週の月曜日を計算してlocalStorageに保存
   * @param {string} dateStr - YYYY-MM-DD形式の日付
   */
  function saveWeekFromDate(dateStr) {
    if (!dateStr) return

    try {
      const date = new Date(dateStr + 'T00:00:00')
      const dayOfWeek = date.getDay() // 0=日曜日, 1=月曜日, ..., 6=土曜日

      // 月曜日を0とするように調整（日曜日は6になる）
      const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1

      // その週の月曜日を計算
      const monday = new Date(date)
      monday.setDate(date.getDate() - mondayOffset)

      // YYYY-MM-DD形式で保存
      const weekStr = monday.toISOString().split('T')[0]
      saveCurrentWeek(weekStr)
    } catch (error) {
      // 日付解析エラーの場合は何もしない
    }
  }

  // 連続更新リクエストの管理用キュー
  // 複数のリクエストが短時間で来た場合に最新のリクエストだけを処理する
  let calendarUpdateQueue = []
  let calendarUpdateTimer = null

  // ユーザーカレンダー更新用キュー
  let userCalendarUpdateQueue = []
  let userCalendarUpdateTimer = null
  let userCalendarRefreshInProgress = false

  /**
   * #calendar を丸ごと再取得して置き換える
   * @param {string|null} month - YYYY-MM
   */
  function refreshCalendar(month) {
    // もしmonthがnullなら現在保存されている月を使用
    if (!month) {
      month = getCurrentMonth()
    } else {
      // 新しい月を保存
      saveCurrentMonth(month)
    }

    // 新しいリクエストをキューに追加
    calendarUpdateQueue.push(month)

    // 既存のタイマーがあればキャンセル
    if (calendarUpdateTimer) {
      clearTimeout(calendarUpdateTimer)
    }

    // 短時間に複数のリクエストが来た場合、最後のリクエストのみを処理
    calendarUpdateTimer = setTimeout(() => {
      // キューの最後のリクエストを取得
      const latestMonth = calendarUpdateQueue[calendarUpdateQueue.length - 1]

      // キューをクリア
      calendarUpdateQueue = []
      calendarUpdateTimer = null

      // 実際の更新処理を実行
      executeCalendarUpdate(latestMonth)
    }, 200)
  }

  /**
   * #calendar を週単位で再取得して置き換える
   * @param {string|null} week - YYYY-MM-DD
   */
  function refreshWeekCalendar(week) {
    // もしweekがnullなら現在保存されている週を使用
    if (!week) {
      week = getCurrentWeek()
    } else {
      // 新しい週を保存
      saveCurrentWeek(week)
    }

    // 新しいリクエストをキューに追加
    calendarUpdateQueue.push(week)

    // 既存のタイマーがあればキャンセル
    if (calendarUpdateTimer) {
      clearTimeout(calendarUpdateTimer)
    }

    // 短時間に複数のリクエストが来た場合、最後のリクエストのみを処理
    calendarUpdateTimer = setTimeout(() => {
      // キューの最後のリクエストを取得
      const latestWeek = calendarUpdateQueue[calendarUpdateQueue.length - 1]

      // キューをクリア
      calendarUpdateQueue = []
      calendarUpdateTimer = null

      // 実際の更新処理を実行
      executeWeekCalendarUpdate(latestWeek)
    }, 200)
  }

  /**
   * 実際のカレンダー更新処理を実行
   * @param {string|null} month - YYYY-MM
   */
  function executeCalendarUpdate(month) {
    // カレンダー更新処理中フラグ
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    // リクエスト中フラグをセット
    window.calendarRefreshInProgress = true

    const url = month ? `/attendance?month=${encodeURIComponent(month)}` : '/attendance'

    // htmxリクエスト完了イベントのリスナーを定義
    const afterSwapListener = function (event) {
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterSwap', afterSwapListener)
    }

    const afterRequestListener = function (event) {
      // エラーが発生した場合か、タイムアウトした場合
      if (event.detail.xhr.status !== 200) {
        // リクエスト完了後にフラグをリセット
        window.calendarRefreshInProgress = false
      }
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterRequest', afterRequestListener)
    }

    // イベントリスナーを追加
    window.addEventListener('htmx:afterSwap', afterSwapListener)
    window.addEventListener('htmx:afterRequest', afterRequestListener)

    // フラグのリセット用タイムアウト（万が一イベントが発火しない場合の保険）
    setTimeout(() => {
      if (window.calendarRefreshInProgress) {
        window.calendarRefreshInProgress = false
      }
    }, 5000)

    try {
      // htmxリクエスト送信
      htmx.ajax('GET', url, {
        target: '#calendar',
        swap: 'innerHTML'
      })
    } catch (error) {
      window.calendarRefreshInProgress = false
    }
  }

  /**
   * 実際の週カレンダー更新処理を実行
   * @param {string|null} week - YYYY-MM-DD
   */
  function executeWeekCalendarUpdate(week) {
    // カレンダー更新処理中フラグ
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    // リクエスト中フラグをセット
    window.calendarRefreshInProgress = true

    const url = week ? `/attendance?week=${encodeURIComponent(week)}` : '/attendance'

    // htmxリクエスト完了イベントのリスナーを定義
    const afterSwapListener = function (event) {
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterSwap', afterSwapListener)
    }

    const afterRequestListener = function (event) {
      // エラーが発生した場合か、タイムアウトした場合
      if (event.detail.xhr.status !== 200) {
        // リクエスト完了後にフラグをリセット
        window.calendarRefreshInProgress = false
      }
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterRequest', afterRequestListener)
    }

    // イベントリスナーを追加
    window.addEventListener('htmx:afterSwap', afterSwapListener)
    window.addEventListener('htmx:afterRequest', afterRequestListener)

    // フラグのリセット用タイムアウト（万が一イベントが発火しない場合の保険）
    setTimeout(() => {
      if (window.calendarRefreshInProgress) {
        window.calendarRefreshInProgress = false
      }
    }, 5000)

    try {
      // htmxリクエスト送信
      htmx.ajax('GET', url, {
        target: '#calendar',
        swap: 'innerHTML'
      })
    } catch (error) {
      window.calendarRefreshInProgress = false
    }
  }

  /**
   * 勤怠登録ページのユーザーカレンダーを更新する
   * @param {string} userId - ユーザーID
   * @param {string|null} month - YYYY-MM形式の月
   */
  function refreshUserCalendar(userId, month) {
    if (!userId) {
      return
    }

    // 現在のURLがregisterページでなければ何もしない
    const isRegisterPage = window.location.pathname.includes('/register')
    if (!isRegisterPage) {
      return
    }

    const userCalendar = document.getElementById('user-calendar')
    if (!userCalendar) {
      return
    }

    // 新しいリクエストをキューに追加
    userCalendarUpdateQueue.push({ userId, month })

    // 既存のタイマーがあればキャンセル
    if (userCalendarUpdateTimer) {
      clearTimeout(userCalendarUpdateTimer)
    }

    // 短時間に複数のリクエストが来た場合、最後のリクエストのみを処理
    userCalendarUpdateTimer = setTimeout(() => {
      // キューの最後のリクエストを取得
      const latestRequest = userCalendarUpdateQueue[userCalendarUpdateQueue.length - 1]

      // キューをクリア
      userCalendarUpdateQueue = []
      userCalendarUpdateTimer = null

      // 実際の更新処理を実行
      if (!userCalendarRefreshInProgress) {
        executeUserCalendarUpdate(latestRequest.userId, latestRequest.month)
      }
    }, 200)
  }

  /**
   * 実際のユーザーカレンダー更新処理を実行
   * @param {string} userId - ユーザーID
   * @param {string|null} month - YYYY-MM形式の月
   */
  function executeUserCalendarUpdate(userId, month) {
    userCalendarRefreshInProgress = true

    // monthがnullの場合は、localStorageから保存された月を取得
    if (!month) {
      month = getCurrentMonth()
    } else {
      // 月の指定があれば保存
      saveCurrentMonth(month)
    }

    const url = month
      ? `/register/${encodeURIComponent(userId)}?month=${encodeURIComponent(month)}`
      : `/register/${encodeURIComponent(userId)}`

    try {
      // htmxリクエスト送信前にリスナー追加
      const beforeSwapListener = function (event) {
        window.removeEventListener('htmx:beforeSwap', beforeSwapListener)
      }

      const afterSwapListener = function (event) {
        userCalendarRefreshInProgress = false
        window.removeEventListener('htmx:afterSwap', afterSwapListener)
      }

      const afterRequestListener = function (event) {
        if (event.detail.xhr.status !== 200) {
          userCalendarRefreshInProgress = false
        }
        window.removeEventListener('htmx:afterRequest', afterRequestListener)
      }

      window.addEventListener('htmx:beforeSwap', beforeSwapListener)
      window.addEventListener('htmx:afterSwap', afterSwapListener)
      window.addEventListener('htmx:afterRequest', afterRequestListener)

      // フラグのリセット用タイムアウト（万が一イベントが発火しない場合の保険）
      setTimeout(() => {
        if (userCalendarRefreshInProgress) {
          userCalendarRefreshInProgress = false
        }
      }, 5000)

      // htmxリクエスト送信
      htmx.ajax('GET', url, {
        target: '#user-calendar',
        swap: 'innerHTML'
      })
    } catch (error) {
      userCalendarRefreshInProgress = false
    }
  }

  /**
   * HX-Trigger ヘッダーを共通で処理
   * @param {XMLHttpRequest} xhr
   */
  function handleTrigger(xhr) {
    const trigHeader = xhr.getResponseHeader('HX-Trigger')
    if (!trigHeader) return

    let triggers
    try {
      triggers = JSON.parse(trigHeader)
    } catch (e) {
      // 文字列として処理を試みる
      if (trigHeader.startsWith('openModal:')) {
        document.getElementById(trigHeader.split(':')[1])?.showModal()
      }
      if (trigHeader.startsWith('closeModal:')) {
        document.getElementById(trigHeader.split(':')[1])?.close()
      }
      return
    }

    // モーダル開閉
    if (triggers.openModal) {
      document.getElementById(triggers.openModal)?.showModal()
    }
    if (triggers.closeModal) {
      document.getElementById(triggers.closeModal)?.close()
    }

    // 勤怠登録ページのユーザーカレンダー更新（モーダル成功時）
    if (triggers.refreshRegisterCalendar) {
      const data = triggers.refreshRegisterCalendar
      setTimeout(() => {
        // localStorageの月情報を更新
        if (data.month) {
          saveCurrentMonth(data.month)
        }
        refreshUserCalendar(data.userId, data.month)
      }, 10)
      return // 他のリフレッシュは処理しない
    }

    // カレンダー再描画（登録／更新／削除後）
    // リフレッシュフラグとイベント処理の競合を避けるため、refreshUserAttendanceとrefreshAttendanceは
    // 一度に1つだけ処理し、少し遅延させて実行する
    if (triggers.refreshUserAttendance) {
      // 勤怠登録ページの場合は、ユーザーカレンダーだけを更新する
      const isRegisterPage = window.location.pathname.includes('/register')
      if (isRegisterPage) {
        setTimeout(() => {
          const userId = triggers.refreshUserAttendance.user_id
          let month = triggers.refreshUserAttendance.month

          // monthがnullまたは未定義の場合、localStorageから取得を試みる
          if (!month) {
            month = getCurrentMonth()
          }

          // localStorageの月情報を更新
          if (month) {
            saveCurrentMonth(month)
          }

          refreshUserCalendar(userId, month)
        }, 10)
      } else {
        // 勤怠管理ページの場合は週カレンダーを更新
        setTimeout(() => {
          const week = triggers.refreshUserAttendance.week || getCurrentWeek()
          const month = triggers.refreshUserAttendance.month || getCurrentMonth()

          // localStorageの週・月情報を更新
          if (week) {
            saveCurrentWeek(week)
          }
          if (month) {
            saveCurrentMonth(month)
          }

          // 週情報があれば週カレンダー、なければ月カレンダーを更新
          if (week) {
            refreshWeekCalendar(week)
          } else {
            refreshCalendar(month)
          }
        }, 10)
      }
      return // refreshAttendanceは処理しない
    }

    if (triggers.refreshAttendance) {
      // この処理は上記のrefreshUserAttendanceが実行されなかった場合のみ実行される
      setTimeout(() => {
        const week = triggers.refreshAttendance.week
        const month = triggers.refreshAttendance.month

        // localStorageの週・月情報を更新
        if (week) {
          saveCurrentWeek(week)
        }
        if (month) {
          saveCurrentMonth(month)
        }

        // 週情報があれば週カレンダー、なければ月カレンダーを更新
        if (week) {
          refreshWeekCalendar(week)
        } else {
          refreshCalendar(month)
        }
      }, 10)
    }
  }

  // カスタムイベントリスナー - モーダル成功時の処理
  document.addEventListener('modalSuccess', function (e) {
    // 現在表示中のユーザーカレンダーをリロード
    const userCalendar = document.getElementById('user-calendar')
    if (userCalendar && userCalendar.dataset.userId) {
      const userId = userCalendar.dataset.userId
      const month = userCalendar.dataset.month || ''

      // localStorageの月情報を更新
      if (month) {
        saveCurrentMonth(month)
      }

      // 現在の月情報を使用してユーザーカレンダーをリロード
      refreshUserCalendar(userId, month)
    }
  })

  // refreshRegisterCalendarイベントのリスナーを追加
  document.addEventListener('refreshRegisterCalendar', function (e) {
    // カスタムイベントから値を取得
    const userId =
      e.detail && e.detail.userId ? e.detail.userId : e.target ? e.target.getAttribute('data-user-id') : null
    const month = e.detail && e.detail.month ? e.detail.month : e.target ? e.target.getAttribute('data-month') : null

    if (userId) {
      // localStorageの月情報を更新
      if (month) {
        saveCurrentMonth(month)
      }

      // ユーザーカレンダーをリロード
      refreshUserCalendar(userId, month)
    }
  })

  // htmxリクエスト前に月・週情報を保存
  window.addEventListener('htmx:beforeRequest', function (e) {
    const elt = e.detail.elt
    // クリックされた要素がswitcherのボタンかチェック
    if (elt.tagName === 'BUTTON' && elt.hasAttribute('hx-get')) {
      const url = new URL(elt.getAttribute('hx-get'), window.location.origin)
      const monthParam = url.searchParams.get('month')
      const weekParam = url.searchParams.get('week')

      if (monthParam) {
        saveCurrentMonth(monthParam)
      } else if (weekParam) {
        saveCurrentWeek(weekParam)
      } else if (elt.textContent.trim() === '今月') {
        // 「今月」ボタンの場合は現在の月を保存（サーバー側で判断）
        localStorage.removeItem('selectedMonth')
      } else if (elt.textContent.trim() === '今週') {
        // 「今週」ボタンの場合は現在の週を保存（サーバー側で判断）
        localStorage.removeItem('selectedWeek')
      }
    }
  })

  // コンテンツ置換後
  window.addEventListener('htmx:afterOnLoad', (e) => {
    // カレンダー更新中のフラグをリセット（念のため）
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    // URLに月・週の情報がある場合はlocalStorageに保存
    saveMonthFromUrl()
    saveWeekFromUrl()
    handleTrigger(e.detail.xhr)
  })

  // 204 No Content などで置換が発生しないケース
  window.addEventListener('htmx:afterRequest', (e) => {
    // カレンダー更新中のフラグをリセット（念のため）
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    handleTrigger(e.detail.xhr)
  })

  // htmxのエラー発生時
  window.addEventListener('htmx:responseError', (e) => {
    // カレンダー更新中のフラグをリセット
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }
    // ユーザーカレンダー更新中フラグをリセット
    if (userCalendarRefreshInProgress) {
      userCalendarRefreshInProgress = false
    }
  })

  // htmxのスワップエラー発生時
  window.addEventListener('htmx:swapError', (e) => {
    // カレンダー更新中のフラグをリセット
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }
    // ユーザーカレンダー更新中フラグをリセット
    if (userCalendarRefreshInProgress) {
      userCalendarRefreshInProgress = false
    }
  })

  // ページ読み込み時
  document.addEventListener('DOMContentLoaded', () => {
    saveMonthFromUrl()
    saveWeekFromUrl()

    // localStorageに週情報があり、かつURLに週情報がない場合は保存された週のカレンダーを読み込む
    const urlParams = new URLSearchParams(window.location.search)
    const weekInUrl = urlParams.get('week')
    const monthInUrl = urlParams.get('month')
    const savedWeek = localStorage.getItem('selectedWeek')
    const savedMonth = localStorage.getItem('selectedMonth')

    if (window.location.pathname.includes('/attendance')) {
      if (savedWeek && !weekInUrl && !monthInUrl) {
        refreshWeekCalendar(savedWeek)
      } else if (savedMonth && !monthInUrl && !weekInUrl) {
        refreshCalendar(savedMonth)
      }
    }
  })

  // グローバル関数として公開
  window.refreshCalendar = refreshCalendar
  window.refreshWeekCalendar = refreshWeekCalendar
  window.saveWeekFromDate = saveWeekFromDate
})()

/**
 * 指定された週のページに遷移する
 * @param {string} week - YYYY-MM-DD形式の週（月曜日）、空文字の場合は現在の週
 * @param {string|null} userId - ユーザーID（指定された場合）
 * @param {string} urlBase - 基本URL
 */
function navigateToWeek(week, userId, urlBase = '/attendance') {
  // 週情報をlocalStorageに保存
  if (week) {
    localStorage.setItem('selectedWeek', week)
  } else {
    localStorage.removeItem('selectedWeek')
  }

  // URLを構築
  let url
  if (userId) {
    url = `${urlBase}/${userId}${week ? `?week=${week}` : ''}`
  } else {
    url = `${urlBase}${week ? `?week=${week}` : ''}`
  }

  // ページ遷移
  window.location.href = url
}
