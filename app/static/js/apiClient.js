;(function () {
  'use strict'

  /**
   * APIクライアント エラーオブジェクト
   */
  class ApiClientError extends Error {
    constructor(message, status, responseData) {
      super(message)
      this.name = 'ApiClientError'
      this.status = status
      this.responseData = responseData
    }
  }

  /**
   * レスポンスを処理し、エラーがあれば例外をスローする共通ハンドラ
   * @param {Response} response - Fetch API の Response オブジェクト
   * @returns {Promise<any>} - 成功時はレスポンスボディをパースした Promise、エラー時は reject された Promise
   */
  async function handleResponse(response) {
    if (!response.ok) {
      let errorData = null
      try {
        // エラーレスポンスに詳細情報が含まれているか試みる
        errorData = await response.json()
      } catch (e) {
        // JSONパースに失敗した場合
        console.warn('Failed to parse error response body as JSON.')
      }
      const errorMessage = errorData?.detail || `サーバーエラー (${response.status})`
      throw new ApiClientError(errorMessage, response.status, errorData)
    }

    // 成功時 (本文がない場合もあるのでチェック)
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      try {
        return await response.json()
      } catch (e) {
        // JSON パースに失敗した場合 (例: 空のレスポンスボディ)
        console.warn('Failed to parse success response body as JSON. Returning null.')
        return null // あるいは {} や undefined を返すなど、仕様に応じて決定
      }
    } else if (response.status === 204) {
      // No Content
      return null // または成功を示す { success: true } など
    } else {
      // JSON以外のレスポンスの場合、テキストとして返すか、nullを返すかなど
      console.warn('Non-JSON success response received. Returning null.')
      return null
    }
  }

  /**
   * GETリクエストを実行
   * @param {string} endpoint - APIエンドポイント (例: '/api/users')
   * @returns {Promise<any>} - APIからのレスポンスデータ
   */
  async function get(endpoint) {
    try {
      const response = await fetch(endpoint)
      return await handleResponse(response)
    } catch (error) {
      console.error(`GET ${endpoint} failed:`, error)
      throw error // エラーを再スローして呼び出し元で catch できるようにする
    }
  }

  /**
   * POSTリクエストを実行 (JSONボディ)
   * @param {string} endpoint - APIエンドポイント
   * @param {object} data - 送信するJavaScriptオブジェクト
   * @returns {Promise<any>} - APIからのレスポンスデータ
   */
  async function postJson(endpoint, data) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
          // 必要に応じて CSRF トークンなどのヘッダーを追加
        },
        body: JSON.stringify(data)
      })
      return await handleResponse(response)
    } catch (error) {
      console.error(`POST (JSON) ${endpoint} failed:`, error)
      throw error
    }
  }

  /**
   * POSTリクエストを実行 (FormDataボディ)
   * @param {string} endpoint - APIエンドポイント
   * @param {FormData} formData - 送信するFormDataオブジェクト
   * @returns {Promise<any>} - APIからのレスポンスデータ
   */
  async function postFormData(endpoint, formData) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        // Content-Type は FormData の場合、ブラウザが自動で設定するため不要
        body: formData
      })
      return await handleResponse(response)
    } catch (error) {
      console.error(`POST (FormData) ${endpoint} failed:`, error)
      throw error
    }
  }

  /**
   * PUTリクエストを実行 (JSONボディ)
   * @param {string} endpoint - APIエンドポイント
   * @param {object} data - 送信するJavaScriptオブジェクト
   * @returns {Promise<any>} - APIからのレスポンスデータ
   */
  async function putJson(endpoint, data) {
    try {
      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      })
      return await handleResponse(response)
    } catch (error) {
      console.error(`PUT ${endpoint} failed:`, error)
      throw error
    }
  }

  /**
   * DELETEリクエストを実行
   * @param {string} endpoint - APIエンドポイント
   * @returns {Promise<any>} - APIからのレスポンスデータ (通常は null か { success: true })
   */
  async function del(endpoint) {
    // deleteは予約語なのでdelを使用
    try {
      const response = await fetch(endpoint, {
        method: 'DELETE'
      })
      // DELETE の成功レスポンスは 204 No Content が多い
      if (response.status === 204) {
        return { success: true } // 成功を示す独自オブジェクトを返す
      }
      return await handleResponse(response)
    } catch (error) {
      console.error(`DELETE ${endpoint} failed:`, error)
      throw error
    }
  }

  // グローバルに公開
  if (typeof window.apiClient === 'undefined') {
    window.apiClient = {
      get,
      postJson,
      postFormData,
      putJson,
      delete: del, // delete メソッドとして公開
      ApiClientError // エラーオブジェクトも公開
    }
  }
})()
