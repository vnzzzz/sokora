/**
 * モーダル操作共通スクリプト
 */

/**
 * 追加フォームのハンドラーを設定
 * @param {string} formId - フォームID
 * @param {string} endpoint - APIエンドポイント
 * @param {string} redirectUrl - 成功時のリダイレクト先URL（省略可）
 * @param {Function} successCallback - 成功時のコールバック関数（省略可）
 */
function setupAddFormHandler(formId, endpoint, redirectUrl = null, successCallback = null) {
  const form = document.getElementById(formId)
  if (!form) return

  form.addEventListener('submit', function (event) {
    event.preventDefault()
    const formData = new FormData(this)
    const data = {}

    // FormDataからJSONに変換
    formData.forEach((value, key) => {
      data[key] = value
    })

    // 送信ボタンを無効化
    const submitBtn = this.querySelector('button[type="submit"]')
    if (submitBtn) {
      submitBtn.disabled = true
      submitBtn.textContent = '送信中...'
    }

    // APIにPOSTリクエスト
    fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((data) => {
            throw new Error(data.detail || 'エラーが発生しました')
          })
        }
        return response.json()
      })
      .then((data) => {
        // 成功時の処理
        if (redirectUrl) {
          window.location.href = redirectUrl
        } else if (successCallback) {
          successCallback(data)
        } else {
          // デフォルトはページリロード
          window.location.reload()
        }
      })
      .catch((error) => {
        alert(error.message || 'エラーが発生しました')
        // エラー時はボタンを元に戻す
        if (submitBtn) {
          submitBtn.disabled = false
          submitBtn.textContent = '追加'
        }
      })
  })
}

/**
 * 編集フォームのハンドラーを一括設定
 * @param {string} selector - ボタンセレクタ
 * @param {string} formIdPrefix - フォームID接頭辞
 * @param {string} endpointTemplate - APIエンドポイントテンプレート
 * @param {Function} successCallback - 成功時のコールバック関数（省略可）
 */
function setupEditFormHandlers(selector, formIdPrefix, endpointTemplate, successCallback = null) {
  document.querySelectorAll(selector).forEach((button) => {
    const form = button.closest('form')
    if (!form) return

    form.addEventListener('submit', function (event) {
      event.preventDefault()

      const itemId = button.getAttribute('data-item-id')
      if (!itemId) return

      const formData = new FormData(this)
      const data = {}

      // FormDataからJSONに変換
      formData.forEach((value, key) => {
        data[key] = value
      })

      // モーダル要素を事前に取得
      const modalElement = button.closest('[x-data*="showEditModal"]')

      // ボタンを無効化
      button.disabled = true
      button.textContent = '保存中...'

      // APIにPUTリクエスト
      fetch(endpointTemplate.replace('{id}', itemId), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      })
        .then((response) => {
          if (!response.ok) {
            return response.json().then((data) => {
              throw new Error(data.detail || 'エラーが発生しました')
            })
          }
          return response.json()
        })
        .then((data) => {
          // 更新されたデータを画面に反映
          updateUIAfterEdit(data, itemId)

          // 成功時の処理
          if (successCallback) {
            successCallback(data, itemId)
          }

          // 処理完了後、モーダルを閉じる (Alpine.jsのモーダルを閉じる)
          if (modalElement) {
            // ボタンを元に戻す
            button.disabled = false
            button.textContent = '保存'

            // モーダルを閉じる（シンプルな方法）
            const closeBtn = modalElement.querySelector('button[type="button"]')
            if (closeBtn) {
              closeBtn.click()
            }
          }
        })
        .catch((error) => {
          alert(error.message || 'エラーが発生しました')

          // エラー時はボタンを元に戻す
          button.disabled = false
          button.textContent = '保存'
        })
    })
  })
}

/**
 * 編集後にUIを更新する
 * @param {Object} data - 更新されたデータ
 * @param {string|number} itemId - アイテムID
 */
function updateUIAfterEdit(data, itemId) {
  if (!data || !itemId) return

  // 社員種別の場合
  const userTypeRow = document.getElementById(`user-type-row-${itemId}`)
  if (userTypeRow && data.name) {
    const nameCell = userTypeRow.querySelector('td:first-child')
    if (nameCell) {
      nameCell.textContent = data.name
    }
  }

  // 勤務場所の場合
  const locationRow = document.getElementById(`location-row-${itemId}`)
  if (locationRow && data.name) {
    const nameCell = locationRow.querySelector('td:first-child span')
    if (nameCell) {
      nameCell.textContent = data.name
    }
  }

  // グループの場合
  const groupRow = document.getElementById(`group-row-${itemId}`)
  if (groupRow && data.name) {
    const nameCell = groupRow.querySelector('td:first-child')
    if (nameCell) {
      nameCell.textContent = data.name
    }
  }

  // ユーザーの場合
  const userRow = document.getElementById(`user-row-${itemId}`)
  if (userRow && data.username) {
    const nameElement = document.getElementById(`user-name-${itemId}`)
    if (nameElement) {
      nameElement.textContent = `${data.username} (${data.user_id})`
    }

    const typeElement = document.getElementById(`user-type-${itemId}`)
    if (typeElement && data.user_type && data.user_type.name) {
      typeElement.textContent = data.user_type.name
    }
  }
}

/**
 * 削除確認のハンドラーを一括設定
 * @param {string} selector - ボタンセレクタ
 * @param {string} endpointTemplate - APIエンドポイントテンプレート
 * @param {Function} successCallback - 成功時のコールバック関数（省略可）
 */
function setupDeleteHandlers(selector, endpointTemplate, successCallback = null) {
  document.querySelectorAll(selector).forEach((button) => {
    const form = button.closest('form')
    if (!form) return

    form.addEventListener('submit', function (event) {
      event.preventDefault()

      const itemId = button.getAttribute('data-item-id')
      if (!itemId) return

      // ボタンが属するモーダルを事前に取得（非同期処理前）
      const modalElement = button.closest('[x-data*="showDeleteConfirm"]')

      // 送信ボタンを無効化
      button.disabled = true
      button.textContent = '処理中...'

      // APIにDELETEリクエスト
      fetch(endpointTemplate.replace('{id}', itemId), {
        method: 'DELETE'
      })
        .then((response) => {
          if (!response.ok) {
            return response.json().then((data) => {
              throw new Error(data.detail || 'エラーが発生しました')
            })
          }
          // 削除成功（204 No Content）の場合
          if (response.status === 204) {
            return {}
          }
          return response.json()
        })
        .then((data) => {
          // モーダルを閉じる
          if (modalElement && typeof modalElement.__x !== 'undefined') {
            modalElement.__x.$data.showDeleteConfirm = false
          }

          // 成功時の処理
          if (successCallback) {
            successCallback(data, itemId)
          } else {
            // デフォルトはページリロード
            window.location.reload()
          }
        })
        .catch((error) => {
          alert(error.message || 'エラーが発生しました')

          // エラー時はボタンを元に戻す
          button.disabled = false
          button.textContent = '削除'

          // モーダルを閉じる
          if (modalElement && typeof modalElement.__x !== 'undefined') {
            modalElement.__x.$data.showDeleteConfirm = false
          }
        })
    })
  })
}
