/* eslint-env browser */
/* globals htmx */
;(function () {
  'use strict'

  /**
   * #calendar を丸ごと再取得して置き換える
   * @param {string|null} month - YYYY-MM
   */
  function refreshCalendar(month) {
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

  // コンテンツ置換後
  window.addEventListener('htmx:afterOnLoad', (e) => {
    handleTrigger(e.detail.xhr)
  })

  // 204 No Content などで置換が発生しないケース
  window.addEventListener('htmx:afterRequest', (e) => {
    handleTrigger(e.detail.xhr)
  })
})()
