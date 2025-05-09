window.addEventListener('htmx:afterOnLoad', (e) => {
  const trigHeader = e.detail.xhr.getResponseHeader('HX-Trigger')
  if (!trigHeader) return

  try {
    // JSONとしてパースを試みる
    const triggers = JSON.parse(trigHeader)

    // openModalアクション
    if (triggers.openModal) {
      const id = triggers.openModal
      document.getElementById(id)?.showModal()
    }

    // closeModalアクション
    if (triggers.closeModal) {
      const id = triggers.closeModal
      document.getElementById(id)?.close()
    }
  } catch (e) {
    // JSONでない場合は文字列として処理（後方互換性のため）
    if (trigHeader.startsWith('openModal:')) {
      const id = trigHeader.split(':')[1]
      document.getElementById(id)?.showModal()
    }
    if (trigHeader.startsWith('closeModal:')) {
      const id = trigHeader.split(':')[1]
      document.getElementById(id)?.close()
    }
  }
})
