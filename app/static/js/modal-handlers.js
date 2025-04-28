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

  form.addEventListener('submit', async function (event) {
    event.preventDefault()
    const formData = new FormData(this)
    const data = {}

    // FormDataからJSONに変換
    formData.forEach((value, key) => {
      // 特定のキーの値を整数に変換
      if (key === 'group_id' || key === 'user_type_id') {
        // parseInt で整数に変換。失敗時は NaN になるので、元の値を使うか、
        // エラーにするかは要件次第。ここでは元の文字列のまま送るよりはマシとして変換を試みる。
        // 失敗時 (NaN) の挙動はバックエンドのバリデーションに任せる。
        const intValue = parseInt(value, 10)
        data[key] = isNaN(intValue) ? value : intValue // 変換失敗時は元の値を保持（バリデーションエラーになるはず）
      } else {
        data[key] = value
      }
    })

    // 送信ボタンを無効化
    const submitBtn = this.querySelector('button[type="submit"]')
    if (submitBtn) {
      submitBtn.disabled = true
      submitBtn.textContent = '送信中...'
    }

    // APIにPOSTリクエスト
    try {
      const responseData = await window.apiClient.postJson(endpoint, data)
      // 成功時の処理
      if (redirectUrl) {
        window.location.href = redirectUrl
      } else if (successCallback) {
        successCallback(responseData)
      } else {
        // デフォルトはページリロード
        window.location.reload()
      }
    } catch (error) {
      console.error('追加処理エラー:', error)
      const message =
        error instanceof window.apiClient.ApiClientError
          ? error.message
          : '追加処理中に予期せぬエラーが発生しました。' + error.message
      alert(message)
      // エラー時はボタンを元に戻す
      if (submitBtn) {
        submitBtn.disabled = false
        // ボタンテキストはフォームによって異なる可能性があるので注意
        // 例: ユーザー追加フォームなら「追加」
        if (formId === 'addUserForm') {
          // 仮のフォームID
          submitBtn.textContent = '追加'
        } else {
          submitBtn.textContent = '送信' // デフォルト
        }
      }
    }
  })
}

/**
 * 編集フォームのハンドラーを一括設定
 * @param {string} selector - ボタンセレクタ
 * @param {string} formIdPrefix - フォームID接頭辞
 * @param {string} endpointTemplate - APIエンドポイントテンプレート (例: '/api/users/{user_id}')
 * @param {Function} successCallback - 成功時のコールバック関数（省略可）
 */
function setupEditFormHandlers(selector, formIdPrefix, endpointTemplate, successCallback = null) {
  document.querySelectorAll(selector).forEach((button) => {
    const form = button.closest('form')
    if (!form) return

    form.addEventListener('submit', async function (event) {
      event.preventDefault()

      const itemId = button.getAttribute('data-item-id')
      if (!itemId) return

      const formData = new FormData(this)
      const data = {}

      // FormDataからJSONに変換
      formData.forEach((value, key) => {
        // 編集時も group_id と user_type_id は整数に変換
        if (key === 'group_id' || key === 'user_type_id') {
          const intValue = parseInt(value, 10)
          data[key] = isNaN(intValue) ? value : intValue
        } else {
          data[key] = value
        }
      })

      // モーダル要素を事前に取得
      const modalElement = button.closest('[x-data*="showEditModal"]')

      // ボタンを無効化
      button.disabled = true
      button.textContent = '保存中...'

      // APIにPUTリクエスト
      const endpoint = endpointTemplate.replace(/\{[a-zA-Z_]+\}/, itemId) // 正規表現でプレースホルダーを置換
      try {
        const responseData = await window.apiClient.putJson(endpoint, data)
        // 更新されたデータを画面に反映
        updateUIAfterEdit(responseData, itemId)

        // 成功時の処理
        if (successCallback) {
          successCallback(responseData, itemId)
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
      } catch (error) {
        console.error('編集処理エラー:', error)
        const message =
          error instanceof window.apiClient.ApiClientError
            ? error.message
            : '編集処理中に予期せぬエラーが発生しました。' + error.message
        alert(message)
        // エラー時はボタンを元に戻す
        button.disabled = false
        button.textContent = '保存'
      }
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
 * @param {string} endpointTemplate - APIエンドポイントテンプレート (例: '/api/users/{user_id}')
 * @param {Function} successCallback - 成功時のコールバック関数（省略可）
 */
function setupDeleteHandlers(selector, endpointTemplate, successCallback = null) {
  document.querySelectorAll(selector).forEach((button) => {
    const form = button.closest('form')
    if (!form) return

    form.addEventListener('submit', async function (event) {
      event.preventDefault()

      const itemId = button.getAttribute('data-item-id')
      if (!itemId) return

      // ボタンが属するモーダルを事前に取得（非同期処理前）
      const modalElement = button.closest('[x-data*="showDeleteConfirm"]')

      // 送信ボタンを無効化
      button.disabled = true
      button.textContent = '処理中...'

      // APIにDELETEリクエスト
      const endpoint = endpointTemplate.replace(/\{[a-zA-Z_]+\}/, itemId) // 正規表現でプレースホルダーを置換
      try {
        // apiClient.delete は成功時 { success: true } を返す想定
        const responseData = await window.apiClient.delete(endpoint)

        if (responseData.success) {
          // モーダルを閉じる
          if (modalElement && typeof modalElement.__x !== 'undefined') {
            // Alpine.js のデータプロパティを直接変更してモーダルを閉じる
            modalElement.__x.$data.showDeleteConfirm = false
          } else {
            // フォールバックとして従来のクリックを試みる (もしAlpineが見つからない場合)
            const closeBtn = modalElement?.querySelector('button[type="button"]')
            closeBtn?.click()
          }

          // 成功時のコールバック関数を実行
          if (successCallback) {
            successCallback(responseData, itemId)
          }
        } else {
          alert('エラー: 削除に失敗しました。(不明な応答)')
        }
      } catch (error) {
        console.error('削除処理エラー:', error)
        const message =
          error instanceof window.apiClient.ApiClientError
            ? error.message
            : '削除処理中に予期せぬエラーが発生しました。' + error.message
        alert(message)
        // エラー時はボタンを元に戻す
        button.disabled = false
        button.textContent = '削除' // または元のテキスト
      }
    })
  })
}
