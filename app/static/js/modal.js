/* eslint-env browser */
/* globals htmx */
;(function () {
  'use strict'

  /**
   * 現在表示中の月を取得する
   * @returns {string|null} YYYY-MM形式の月、または取得できない場合はnull
   */
  function getCurrentMonth() {
    // localStorageから取得
    return localStorage.getItem('selectedMonth')
  }

  /**
   * 表示中の月を保存する
   * @param {string} month - YYYY-MM形式の月
   */
  function saveCurrentMonth(month) {
    if (month) {
      localStorage.setItem('selectedMonth', month)
      console.log('月情報を保存しました:', month)
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

  // 連続更新リクエストの管理用キュー
  // 複数のリクエストが短時間で来た場合に最新のリクエストだけを処理する
  let calendarUpdateQueue = []
  let calendarUpdateTimer = null

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
      console.log(
        `カレンダー更新キュー処理: ${calendarUpdateQueue.length}件のリクエストから最新の月[${
          latestMonth || '現在月'
        }]を処理します`
      )

      // キューをクリア
      calendarUpdateQueue = []
      calendarUpdateTimer = null

      // 実際の更新処理を実行
      executeCalendarUpdate(latestMonth)
    }, 200)
  }

  /**
   * 実際のカレンダー更新処理を実行
   * @param {string|null} month - YYYY-MM
   */
  function executeCalendarUpdate(month) {
    // カレンダー更新処理中フラグ
    if (window.calendarRefreshInProgress) {
      console.log('カレンダー更新処理が進行中です。強制リセットして続行します...')
      window.calendarRefreshInProgress = false
    }

    // リクエスト中フラグをセット
    window.calendarRefreshInProgress = true
    console.log('カレンダー更新フラグをONにしました')

    const url = month ? `/attendance?month=${encodeURIComponent(month)}` : '/attendance'
    console.log('カレンダー更新リクエスト開始:', url)

    // htmxリクエスト完了イベントのリスナーを定義
    const afterSwapListener = function (event) {
      console.log('htmx:afterSwap イベント発生:', event.detail.xhr.responseURL)
      // URL比較ではなく、常に最初の更新完了でフラグをリセット
      console.log('カレンダー更新が完了しました')
      // リクエスト完了後にフラグをリセット
      window.calendarRefreshInProgress = false
      console.log('カレンダー更新フラグをOFFにしました')
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterSwap', afterSwapListener)
    }

    const afterRequestListener = function (event) {
      console.log(
        'htmx:afterRequest イベント発生:',
        event.detail.xhr.responseURL,
        'ステータス:',
        event.detail.xhr.status
      )
      // エラーが発生した場合か、タイムアウトした場合
      if (event.detail.xhr.status !== 200) {
        console.error('カレンダー更新に失敗しました:', event.detail.xhr.status)
        // リクエスト完了後にフラグをリセット
        window.calendarRefreshInProgress = false
        console.log('カレンダー更新フラグをOFFにしました (エラー時)')
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
        console.log('タイムアウトによるカレンダー更新フラグのリセット')
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
      console.error('htmx.ajax 呼び出しでエラーが発生しました:', error)
      window.calendarRefreshInProgress = false
      console.log('カレンダー更新フラグをOFFにしました (例外発生時)')
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
    } catch {
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
      console.log('モーダルが開きました')
    }
    if (triggers.closeModal) {
      document.getElementById(triggers.closeModal)?.close()
      console.log('モーダルが閉じられました')
    }

    // カレンダー再描画（登録／更新／削除後）
    // リフレッシュフラグとイベント処理の競合を避けるため、refreshUserAttendanceとrefreshAttendanceは
    // 一度に1つだけ処理し、少し遅延させて実行する
    if (triggers.refreshUserAttendance) {
      console.log('refreshUserAttendanceトリガーを受信:', triggers.refreshUserAttendance)
      // トリガー処理用に専用の遅延関数を使用
      setTimeout(() => {
        const month = triggers.refreshUserAttendance.month
        console.log('遅延実行: カレンダー更新 (ユーザー):', month || '現在月')
        refreshCalendar(month)
      }, 100)
      console.log('カレンダーがリフレッシュされます（ユーザー）')
      return // refreshAttendanceは処理しない
    }

    if (triggers.refreshAttendance) {
      console.log('refreshAttendanceトリガーを受信:', triggers.refreshAttendance)
      // この処理は上記のrefreshUserAttendanceが実行されなかった場合のみ実行される
      setTimeout(() => {
        const month = triggers.refreshAttendance.month
        console.log('遅延実行: カレンダー更新 (全体):', month || '現在月')
        refreshCalendar(month)
      }, 150)
      console.log('カレンダーがリフレッシュされます（全体）')
    }
  }

  // htmxリクエスト前に月情報を保存
  window.addEventListener('htmx:beforeRequest', function (e) {
    const elt = e.detail.elt
    // クリックされた要素がmonth_switcherのボタンかチェック
    if (elt.tagName === 'BUTTON' && elt.hasAttribute('hx-get')) {
      const url = new URL(elt.getAttribute('hx-get'), window.location.origin)
      const monthParam = url.searchParams.get('month')
      if (monthParam) {
        saveCurrentMonth(monthParam)
      } else if (elt.textContent.trim() === '今月') {
        // 「今月」ボタンの場合は現在の月を保存（サーバー側で判断）
        localStorage.removeItem('selectedMonth')
      }
    }
  })

  // コンテンツ置換後
  window.addEventListener('htmx:afterOnLoad', (e) => {
    // カレンダー更新中のフラグをリセット（念のため）
    if (window.calendarRefreshInProgress) {
      console.log('htmx:afterOnLoad でカレンダー更新フラグをリセットしました')
      window.calendarRefreshInProgress = false
    }

    // URLに月の情報がある場合はlocalStorageに保存
    saveMonthFromUrl()
    handleTrigger(e.detail.xhr)
  })

  // 204 No Content などで置換が発生しないケース
  window.addEventListener('htmx:afterRequest', (e) => {
    // カレンダー更新中のフラグをリセット（念のため）
    if (window.calendarRefreshInProgress) {
      console.log('htmx:afterRequest でカレンダー更新フラグをリセットしました')
      window.calendarRefreshInProgress = false
    }

    handleTrigger(e.detail.xhr)
  })

  // htmxのエラー発生時
  window.addEventListener('htmx:responseError', (e) => {
    console.error('htmx:responseError イベント発生:', e.detail.error)
    // カレンダー更新中のフラグをリセット
    if (window.calendarRefreshInProgress) {
      console.log('htmx:responseError でカレンダー更新フラグをリセットしました')
      window.calendarRefreshInProgress = false
    }
  })

  // htmxのスワップエラー発生時
  window.addEventListener('htmx:swapError', (e) => {
    console.error('htmx:swapError イベント発生:', e.detail.error)
    // カレンダー更新中のフラグをリセット
    if (window.calendarRefreshInProgress) {
      console.log('htmx:swapError でカレンダー更新フラグをリセットしました')
      window.calendarRefreshInProgress = false
    }
  })

  // ページ読み込み時
  document.addEventListener('DOMContentLoaded', () => {
    saveMonthFromUrl()

    // localStorageに月情報があり、かつURLに月情報がない場合は保存された月のカレンダーを読み込む
    const urlParams = new URLSearchParams(window.location.search)
    const monthInUrl = urlParams.get('month')
    const savedMonth = localStorage.getItem('selectedMonth')

    if (savedMonth && !monthInUrl && window.location.pathname.includes('/attendance')) {
      console.log('保存された月情報でカレンダーを読み込みます:', savedMonth)
      refreshCalendar(savedMonth)
    }
  })
})()
