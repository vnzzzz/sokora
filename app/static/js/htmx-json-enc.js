;(function () {
  if (!window.htmx) return

  const jsonEncExtension = {
    encodeParameters: function (xhr, parameters) {
      // Force JSON encoding for non-GET requests
      xhr.setRequestHeader('Content-Type', 'application/json')
      return JSON.stringify(normalizeParams(parameters))
    },
    onEvent: function (name, evt) {
      if (name !== 'htmx:configRequest') return
      const detail = evt.detail
      if (!detail.verb || detail.verb.toLowerCase() === 'get') return
      detail.headers = detail.headers || {}
      detail.headers['Content-Type'] = 'application/json'
      detail.encodeParameters = this.encodeParameters
    },
  }

  function normalizeParams(params) {
    if (!(params instanceof FormData)) return params
    const obj = {}
    for (const [key, value] of params.entries()) {
      if (obj[key] === undefined) {
        obj[key] = value
      } else if (Array.isArray(obj[key])) {
        obj[key].push(value)
      } else {
        obj[key] = [obj[key], value]
      }
    }
    return obj
  }

  htmx.defineExtension('json-enc', jsonEncExtension)
})()
