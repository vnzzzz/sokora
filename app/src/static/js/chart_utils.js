/**
 * Sokora チャートユーティリティ
 * Chart.jsを使用した円グラフ作成機能を提供します
 */

// Chart.js 設定と色
const chartColors = [
  'rgba(74, 222, 128, 0.8)', // 在宅 (緑)
  'rgba(96, 165, 250, 0.8)', // 出社 (青)
  'rgba(251, 146, 60, 0.8)', // 出張 (オレンジ)
  'rgba(167, 139, 250, 0.8)', // 紫
  'rgba(248, 113, 113, 0.8)', // 赤
  'rgba(45, 212, 191, 0.8)', // ティール
  'rgba(250, 204, 21, 0.8)' // 黄色
]

/**
 * 動的な勤務場所円グラフ作成関数
 * @param {string} canvasId - グラフを描画するcanvas要素のID
 * @param {Object} locationData - 場所ごとの人数データ {勤務場所: 人数, ...}
 */
function createDynamicPieChart(canvasId, locationData) {
  const canvas = document.getElementById(canvasId)
  if (!canvas) return

  // 既存のチャートがあれば破棄
  const existingChart = Chart.getChart(canvas)
  if (existingChart) {
    existingChart.destroy()
  }

  // データを配列に変換
  const labels = Object.keys(locationData)
  const data = labels.map((key) => locationData[key])
  const hasData = data.some((value) => value > 0)

  // データがある場合のみグラフを表示
  if (hasData) {
    // 色の割り当て
    const backgroundColor = labels.map((_, index) => chartColors[index % chartColors.length])

    new Chart(canvas, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: backgroundColor
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: true
          },
          datalabels: {
            formatter: (value, ctx) => {
              const label = ctx.chart.data.labels[ctx.dataIndex]
              return `${label}\n${value}名`
            },
            color: '#fff',
            font: {
              weight: 'bold',
              size: 14
            },
            align: 'center',
            anchor: 'center'
          }
        }
      }
    })
  }
}

/**
 * チャートデータ解析関数
 * @param {HTMLElement} chartDataEl - チャートデータを含むHTML要素
 * @returns {Object} locations と summary を含むオブジェクト
 */
function parseChartData(chartDataEl) {
  let locations = []
  let summary = {}

  if (chartDataEl) {
    try {
      const locationsStr = chartDataEl.dataset.locations || '[]'
      const summaryStr = chartDataEl.dataset.summary || '{}'

      // 空文字列のチェック
      if (locationsStr && locationsStr.trim()) {
        locations = JSON.parse(locationsStr)
      }

      if (summaryStr && summaryStr.trim()) {
        summary = JSON.parse(summaryStr)
      }
    } catch (error) {
      console.error('データ解析エラー:', error)
    }
  }

  return { locations, summary }
}

/**
 * HTMXイベントリスナーとチャート初期化
 */
document.addEventListener('DOMContentLoaded', function () {
  // Chart.jsプラグイン登録
  if (typeof Chart !== 'undefined' && typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels)
  }

  // 初期表示時のチャート描画
  const chartDataEl = document.getElementById('default-chart-data')
  if (chartDataEl) {
    try {
      const { locations, summary } = parseChartData(chartDataEl)

      // オブジェクトに変換
      const locationData = {}
      for (const location of locations) {
        locationData[location] = summary[location] || 0
      }

      // チャート描画
      createDynamicPieChart('location-pie-chart', locationData)
    } catch (error) {
      console.error('チャート描画エラー:', error)
    }
  }

  // HTMXイベントリスナー
  document.addEventListener('htmx:afterSwap', function (event) {
    // 詳細エリアが更新されたときのチャート描画
    if (event.detail.target.id === 'detail-area' || event.detail.target.id === 'calendar-area') {
      const chartDataEl = document.getElementById('chart-data') || document.getElementById('default-chart-data')
      const locationChart = document.getElementById('location-pie-chart')

      if (chartDataEl && locationChart) {
        try {
          const { locations, summary } = parseChartData(chartDataEl)

          // データの準備
          const locationData = {}
          for (const location of locations) {
            locationData[location] = summary[location] || 0
          }

          // チャート描画
          createDynamicPieChart('location-pie-chart', locationData)
        } catch (error) {
          console.error('チャート更新エラー:', error)
        }
      }
    }
  })
})
