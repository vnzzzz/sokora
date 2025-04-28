;(function () {
  'use strict'

  // --- グローバルに公開するハンドラ ---
  if (typeof window.attendanceHandlers === 'undefined') {
    window.attendanceHandlers = {}
  }

  // --- Helper Functions ---

  /**
   * 日本語の日付フォーマット関数
   * @param {string} dateStr - YYYY-MM-DD 形式の日付文字列
   * @returns {string} YYYY年M月D日(曜) 形式の文字列
   */
  function formatDateJa(dateStr) {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      // Dateオブジェクトが有効かチェック (無効な日付文字列対策)
      if (isNaN(date.getTime())) {
        console.error('Invalid date string for formatDateJa:', dateStr)
        return '無効な日付'
      }
      const year = date.getFullYear()
      const month = date.getMonth() + 1
      const day = date.getDate()
      const weekdays = ['日', '月', '火', '水', '木', '金', '土']
      const weekday = weekdays[date.getDay()]
      return `${year}年${month}月${day}日(${weekday})`
    } catch (e) {
      console.error('Error formatting date:', dateStr, e)
      return '日付エラー'
    }
  }

  // --- イベントハンドラ ---

  /**
   * 勤怠セルクリック時の処理
   * @param {Event} event - クリックイベント
   */
  async function handleAttendanceCellClick(event) {
    if (event.target.closest('.attendance-cell')) {
      const cell = event.target.closest('.attendance-cell')
      const userId = cell.dataset.userId
      const userName = cell.dataset.userName
      const date = cell.dataset.date
      const hasData = cell.dataset.hasData === 'true'
      // const locationName = cell.dataset.location || ''; // 古い locationName は不要かも

      let attendanceId = null
      let currentLocationId = null

      // データを取得して最新の状態を確認 (hasData によらず確認)
      try {
        const endpoint = `/api/attendances/user/${userId}?date=${date}`
        const userData = await window.apiClient.get(endpoint)
        if (userData && userData.dates && userData.dates.length > 0) {
          // 該当日のデータが存在する場合
          const attendanceData = userData.dates[0] // 1日1レコード前提
          attendanceId = attendanceData.attendance_id
          currentLocationId = attendanceData.location_id
        } else {
          // 該当日のデータが存在しない場合
          attendanceId = null
          currentLocationId = null
        }
      } catch (error) {
        console.error(`Failed to fetch attendance data for ${userId} on ${date}:`, error)
        // エラーが発生してもモーダルは開くが、IDは null のまま
        alert('勤怠データの取得に失敗しました。モーダルは表示されますが、更新/削除ができない可能性があります。')
      }

      // カスタムイベントでモーダルを開く
      window.dispatchEvent(
        new CustomEvent('open-attendance-modal', {
          detail: {
            userId,
            userName,
            date,
            attendanceId, // APIから取得したID
            locationId: currentLocationId, // APIから取得した現在のLocation ID
            hasData: !!attendanceId, // attendanceId があればデータありとみなす
            formattedDate: formatDateJa(date)
          }
        })
      )
    }
  }

  /**
   * 勤怠登録処理 (Alpineモーダルから呼び出される)
   */
  async function submitAttendance() {
    const form = document.getElementById('attendance-form')
    if (!form) {
      console.error('Attendance form not found.')
      alert('登録フォームが見つかりません。ページの再読み込みをお試しください。')
      return
    }
    const formData = new FormData(form)

    // 送信ボタンを無効化（ユーザーフィードバック）
    const submitButton = form.querySelector('button[type="button"].btn-neutral')
    if (submitButton) {
      submitButton.disabled = true
      submitButton.classList.add('loading') // DaisyUI loading スピナー
    }

    try {
      const data = await window.apiClient.postFormData('/api/attendances/', formData)
      // 成功時の処理: APIは作成された Attendance オブジェクトを返すので、その存在チェック (例: idがあるか) で成功を判断
      if (data && data.id) {
        // data.success の代わりに data.id の存在をチェック
        window.dispatchEvent(new CustomEvent('close-attendance-modal'))
        htmx.trigger(document.body, 'refreshAttendance', {})
      } else {
        // APIは成功(2xx)だが、期待したデータが返ってこなかった場合 (通常は起こらないはず)
        alert('エラー: 勤怠の登録に失敗しました (不明な応答)')
      }
    } catch (error) {
      console.error('勤怠登録エラー:', error)
      // error が ApiClientError のインスタンスかチェック
      const message =
        error instanceof window.apiClient.ApiClientError
          ? error.message
          : '勤怠の登録処理中に予期せぬエラーが発生しました。' + error.message
      alert(message)
    } finally {
      // 送信ボタンの状態を元に戻す
      if (submitButton) {
        submitButton.disabled = false
        submitButton.classList.remove('loading')
      }
    }
  }

  /**
   * 勤怠削除処理 (Alpineモーダルから呼び出される)
   * @param {string} userId - ユーザーID
   * @param {string} date - 日付 (YYYY-MM-DD)
   */
  async function deleteAttendance(userId, date) {
    if (!userId || !date) {
      alert('削除に必要な情報が不足しています。')
      return
    }

    // 削除ボタンを無効化
    // Alpineコンポーネント内のボタンを取得するのは難しいので、
    // 一旦モーダル全体から削除ボタンを探す (より良い方法は検討の余地あり)
    const deleteButton = document.querySelector('#attendance-form button[type="button"].btn-error')
    if (deleteButton) {
      deleteButton.disabled = true
      deleteButton.classList.add('loading')
    }

    const endpoint = `/api/attendances/?user_id=${encodeURIComponent(userId)}&date=${encodeURIComponent(date)}`
    try {
      // apiClient.delete は成功時 { success: true } を返す想定
      const data = await window.apiClient.delete(endpoint)
      if (data.success) {
        // dataがnullでない、かつsuccessプロパティがtrueか
        window.dispatchEvent(new CustomEvent('close-attendance-modal'))
        htmx.trigger(document.body, 'refreshAttendance', {})
      } else {
        // 削除APIが成功(2xx)だが想定外のレスポンスを返した場合
        // (apiClient.deleteの実装によってはここに来ない可能性もある)
        alert('エラー: 勤怠の削除に失敗しました。(不明な応答)')
      }
    } catch (error) {
      console.error('勤怠削除エラー:', error)
      const message =
        error instanceof window.apiClient.ApiClientError
          ? error.message
          : '勤怠の削除処理中に予期せぬエラーが発生しました。' + error.message
      alert(message)
    } finally {
      // 削除ボタンの状態を元に戻す
      if (deleteButton) {
        deleteButton.disabled = false
        deleteButton.classList.remove('loading')
      }
    }
  }

  /**
   * 勤怠更新処理 (Alpineモーダルから呼び出される)
   * @param {number} attendanceId - 更新対象の勤怠ID
   * @param {number|string} locationId - 新しい勤務場所ID
   */
  async function updateAttendance(attendanceId, locationId) {
    if (!attendanceId || locationId === null || locationId === undefined) {
      alert('更新に必要な情報が不足しています。')
      return
    }

    const form = document.getElementById('attendance-form') // ボタン取得用
    const submitButton = form?.querySelector('button[type="button"].btn-neutral')
    if (submitButton) {
      submitButton.disabled = true
      submitButton.classList.add('loading')
    }

    const endpoint = `/api/attendances/${attendanceId}`
    // AttendanceUpdate スキーマに合わせる
    const data = { location_id: parseInt(locationId, 10) } // 数値に変換

    if (isNaN(data.location_id)) {
      alert('無効な勤務場所が選択されました。')
      if (submitButton) {
        submitButton.disabled = false
        submitButton.classList.remove('loading')
      }
      return
    }

    try {
      // apiClient.putJson は成功時パースされたJSONを返す想定
      const responseData = await window.apiClient.putJson(endpoint, data)
      // API が成功レスポンス (例: 更新後の Attendance オブジェクト) を返すと仮定
      window.dispatchEvent(new CustomEvent('close-attendance-modal'))
      htmx.trigger(document.body, 'refreshAttendance', {})
    } catch (error) {
      console.error('勤怠更新エラー:', error)
      const message =
        error instanceof window.apiClient.ApiClientError
          ? error.message
          : '勤怠の更新処理中に予期せぬエラーが発生しました。' + error.message
      alert(message)
    } finally {
      if (submitButton) {
        submitButton.disabled = false
        submitButton.classList.remove('loading')
      }
    }
  }

  // --- 初期化処理 ---

  /**
   * 勤怠ページの初期化（イベントリスナー設定など）
   */
  function initAttendancePage() {
    // クリックイベントリスナー（イベント委譲）
    document.body.removeEventListener('click', handleAttendanceCellClick) // 重複防止
    document.body.addEventListener('click', handleAttendanceCellClick)

    // Alpineコンポーネントから呼び出せるように関数を公開
    window.attendanceHandlers.submitAttendance = submitAttendance
    window.attendanceHandlers.deleteAttendance = deleteAttendance
    window.attendanceHandlers.formatDateJa = formatDateJa
    window.attendanceHandlers.updateAttendance = updateAttendance

    // HTMXコンテンツ置換後にも初期化が必要か確認
    // このファイルが読み込まれる attendance/index.html では、
    // #attendance-content が HTMX で更新されるため、
    // 再度 initAttendancePage を呼ぶ必要はないはず
    // (bodyへのリスナーは一度設定すればよいため)

    // location_types_data を読み込むための隠し要素を追加
    // ... (省略) ...
  }

  // --- イベントリスナー設定 ---

  // ページ初期ロード時に初期化を実行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAttendancePage)
  } else {
    // DOMがすでに読み込まれている場合
    initAttendancePage()
  }
})()
