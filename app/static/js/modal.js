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
    const url = month ? `/attendance?month=${encodeURIComponent(month)}` : '/attendance'
    htmx.ajax('GET', url, { target: '#calendar', swap: 'innerHTML' })
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
    if (triggers.refreshUserAttendance) {
      refreshCalendar(triggers.refreshUserAttendance.month)
      console.log('カレンダーがリフレッシュされました')
    }
    if (triggers.refreshAttendance) {
      refreshCalendar(triggers.refreshAttendance.month)
      console.log('カレンダーがリフレッシュされました')
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
    // URLに月の情報がある場合はlocalStorageに保存
    saveMonthFromUrl()
    handleTrigger(e.detail.xhr)
  })

  // 204 No Content などで置換が発生しないケース
  window.addEventListener('htmx:afterRequest', (e) => {
    handleTrigger(e.detail.xhr)
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
