// 丸いfaviconを設定する関数
function setCircularFavicon() {
  // Canvasを作成
  const canvas = document.createElement('canvas')
  const size = 32 // faviconのサイズ
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')

  // 画像を読み込む
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.src = '/static/favicon.ico'

  // 画像が読み込まれたら処理を実行
  img.onload = function () {
    // 円形のクリッピングパスを作成
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2, true)
    ctx.closePath()
    ctx.clip()

    // 画像を描画
    ctx.drawImage(img, 0, 0, size, size)

    // 円形のfaviconとして設定
    const faviconLink = document.querySelector('link[rel="icon"]')
    if (faviconLink) {
      faviconLink.href = canvas.toDataURL()
    } else {
      const link = document.createElement('link')
      link.rel = 'icon'
      link.href = canvas.toDataURL()
      document.head.appendChild(link)
    }
  }
}

// ページ読み込み時に実行
window.addEventListener('load', setCircularFavicon)
