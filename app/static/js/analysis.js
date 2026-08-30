/**
 * 勤怠集計ページのJavaScript
 */

// グローバル変数
let selectedLocationId = null
let selectedLocationName = ''

// 統合ページ用のJavaScript関数
function initializeAnalysisPage(config) {
  const isDetailMode = Boolean(config?.isDetailMode)
  const locationDetails = config?.locationDetails || {}
  const period = config?.period || {}

  const setup = () => {
    // テーブルの横スクロール時のヘッダー固定を改善
    const tables = document.querySelectorAll('.overflow-x-auto')
    tables.forEach((table) => {
      table.addEventListener('scroll', function () {
        const stickyHeaders = table.querySelectorAll('th.sticky, td.sticky')
        stickyHeaders.forEach((header) => {
          if (table.scrollLeft > 0) {
            header.style.boxShadow = '2px 0 4px rgba(0,0,0,0.1)'
          } else {
            header.style.boxShadow = 'none'
          }
        })
      })
    })

    // 期間選択の制御
    const periodTypeRadios = document.querySelectorAll('input[name="period-type"]')
    const monthSelection = document.getElementById('month-selection')
    const yearSelection = document.getElementById('year-selection')
    const monthInput = document.getElementById('month-input')
    const yearSelect = document.getElementById('year-select')
    const isYearMode = period?.mode === 'fiscal_year'

    // 期間タイプ変更時の処理
    periodTypeRadios.forEach((radio) => {
      radio.addEventListener('change', function () {
        if (this.value === 'month') {
          monthSelection.classList.remove('hidden')
          yearSelection.classList.add('hidden')
        } else {
          monthSelection.classList.add('hidden')
          yearSelection.classList.remove('hidden')
        }
      })
    })

    if (isYearMode) {
      monthSelection?.classList.add('hidden')
      yearSelection?.classList.remove('hidden')
    }

    const swapAnalysisContent = (url) => {
      const root = document.getElementById('analysis-root')
      if (!root) {
        window.location.href = url
        return
      }

      fetch(url, { headers: { 'X-Requested-With': 'fetch' } })
        .then((res) => res.text())
        .then((html) => {
          const parser = new DOMParser()
          const doc = parser.parseFromString(html, 'text/html')
          const newRoot = doc.getElementById('analysis-root')
          const newConfigScript = doc.getElementById('analysis-config')
          const newLabel = doc.querySelector('.analysis-period-label')
          if (!newRoot || !newConfigScript) {
            window.location.href = url
            return
          }
          root.replaceWith(newRoot)
          if (newLabel) {
            const currentLabel = document.querySelector('.analysis-period-label')
            if (currentLabel) {
              currentLabel.textContent = newLabel.textContent
            }
          }
          history.pushState({}, '', url)

          const newConfig = JSON.parse(newConfigScript.textContent)
          initializeAnalysisPage(newConfig)
        })
        .catch(() => {
          window.location.href = url
        })
    }

    const navigateToPeriod = (target) => {
      let url = '/analysis'
      if (target === 'month') {
        const selectedMonth = monthInput ? monthInput.value : ''
        if (selectedMonth) {
          url += `?month=${selectedMonth}`
        }
      } else {
        const selectedYear = yearSelect ? yearSelect.value : ''
        if (selectedYear) {
          url += `?mode=year&year=${selectedYear}`
        }
      }
      swapAnalysisContent(url)
    }

    if (monthInput) {
      monthInput.addEventListener('change', () => {
        const monthRadio = document.getElementById('period-month')
        if (monthRadio) monthRadio.checked = true
        navigateToPeriod('month')
      })
    }

    if (yearSelect) {
      yearSelect.addEventListener('change', () => {
        const yearRadio = document.getElementById('period-year')
        if (yearRadio) yearRadio.checked = true
        navigateToPeriod('year')
      })
    }

    periodTypeRadios.forEach((radio) => {
      radio.addEventListener('change', function () {
        if (this.value === 'month') {
          navigateToPeriod('month')
        } else {
          navigateToPeriod('year')
        }
      })
    })

    if (!isDetailMode) {
      // 勤怠種別チェックボックスの制御（月集計モード）
      const checkboxes = document.querySelectorAll('.location-checkbox')
      const toggleLocationColumn = (locationId, isChecked) => {
        const headers = document.querySelectorAll('.location-header[data-location-id="' + locationId + '"]')
        const cells = document.querySelectorAll('.location-cell[data-location-id="' + locationId + '"]')

        headers.forEach((header) => {
          header.style.display = isChecked ? '' : 'none'
        })

        cells.forEach((cell) => {
          cell.style.display = isChecked ? '' : 'none'
        })
      }

      checkboxes.forEach((checkbox) => {
        toggleLocationColumn(checkbox.dataset.locationId, checkbox.checked)
        checkbox.addEventListener('change', function () {
          const locationId = this.dataset.locationId
          const isChecked = this.checked

          toggleLocationColumn(locationId, isChecked)

          // 詳細データを更新
          updateDetailColumns(locationDetails)
        })
      })

      // 初期表示時に詳細データを更新（DOMContentLoaded後に実行）
      updateDetailColumns(locationDetails)
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup, { once: true })
  } else {
    setup()
  }
}

// 詳細列のデータを更新する関数
function updateDetailColumns(locationDetails) {
  // 選択された勤怠種別IDリストを取得
  const checkedBoxes = document.querySelectorAll('.location-checkbox:checked')
  const selectedLocationIds = Array.from(checkedBoxes).map((cb) => parseInt(cb.dataset.locationId))

  // 勤怠種別名のマッピングを作成
  const locationNames = {}
  document.querySelectorAll('.location-checkbox').forEach((cb) => {
    locationNames[parseInt(cb.dataset.locationId)] = cb.dataset.locationName
  })

  // 詳細データを各行に表示
  const detailCountCells = document.querySelectorAll('.detail-count-cell')
  const detailDatesCells = document.querySelectorAll('.detail-dates-cell')

  detailCountCells.forEach((cell) => {
    const row = cell.closest('tr')
    const userId = row.querySelector('.detail-dates-cell')
      ? row.querySelector('.detail-dates-cell').dataset.userId
      : null

    if (userId && selectedLocationIds.length > 0) {
      // 選択された勤怠種別の合算日数を計算
      let totalDays = 0
      selectedLocationIds.forEach((locationId) => {
        if (locationDetails[locationId] && locationDetails[locationId][userId]) {
          totalDays += locationDetails[locationId][userId].length
        }
      })

      const countSpan = cell.querySelector('span')
      if (countSpan) {
        if (totalDays > 0) {
          countSpan.textContent = totalDays
          countSpan.className = 'badge badge-primary badge-sm'
        } else {
          countSpan.textContent = '-'
          countSpan.className = 'text-base-content/30'
        }
      }
    } else {
      const countSpan = cell.querySelector('span')
      if (countSpan) {
        countSpan.textContent = '-'
        countSpan.className = 'text-base-content/30'
      }
    }
  })

  detailDatesCells.forEach((cell) => {
    const userId = cell.dataset.userId
    const datesDiv = cell.querySelector('div')

    if (userId && selectedLocationIds.length > 0) {
      // 勤怠種別ごとに日付をグループ化
      const locationGroups = {}
      selectedLocationIds.forEach((locationId) => {
        if (locationDetails[locationId] && locationDetails[locationId][userId]) {
          const dates = locationDetails[locationId][userId]
          if (dates.length > 0) {
            locationGroups[locationId] = dates.sort((a, b) => new Date(a.date_str) - new Date(b.date_str))
          }
        }
      })

      // 親divのflexレイアウトを無効にして、block要素に変更
      datesDiv.className = 'text-sm'
      datesDiv.innerHTML = ''

      if (Object.keys(locationGroups).length > 0) {
        // 勤怠種別ごとに表示
        Object.keys(locationGroups).forEach((locationId) => {
          const locationName = locationNames[locationId]
          const dates = locationGroups[locationId]

          // 勤怠種別ごとのコンテナ
          const locationContainer = document.createElement('div')
          locationContainer.className = 'mb-2'

          // 勤怠種別名と日付を一行で表示
          const content = document.createElement('div')
          content.className = 'text-sm'

          // 勤怠種別名
          const typeSpan = document.createElement('span')
          typeSpan.className = 'font-medium text-base-content'
          typeSpan.textContent = locationName + ': '
          content.appendChild(typeSpan)

          // 日付のリスト
          dates.forEach((dateInfo, index) => {
            const dateSpan = document.createElement('span')
            dateSpan.className = 'text-base-content'
            dateSpan.title = dateInfo.date_str
            dateSpan.textContent = dateInfo.date_simple
            content.appendChild(dateSpan)

            // 最後の日付以外はスペースを追加
            if (index < dates.length - 1) {
              const spaceSpan = document.createElement('span')
              spaceSpan.textContent = ' '
              content.appendChild(spaceSpan)
            }
          })

          locationContainer.appendChild(content)
          datesDiv.appendChild(locationContainer)
        })
      } else {
        datesDiv.innerHTML = '<span class="text-base-content/30">-</span>'
      }
    } else {
      // 親divのクラスを元に戻す
      datesDiv.className = 'flex flex-wrap gap-2 text-sm'
      datesDiv.innerHTML = '<span class="text-base-content/30">-</span>'
    }
  })
}

/**
 * 指定された月の分析ページに遷移する
 */
function navigateToMonth(month, userId, urlBase) {
  urlBase = urlBase || '/analysis'
  let url = urlBase
  if (month) {
    url += '?month=' + month
  }
  window.location.href = url
}

// グローバルスコープに関数を追加
window.navigateToMonth = navigateToMonth
window.initializeAnalysisPage = initializeAnalysisPage
