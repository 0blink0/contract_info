const { contextBridge, ipcRenderer } = require('electron')

function sanitizeSettings(payload) {
  const input = payload && typeof payload === 'object' ? payload : {}
  const llmBaseUrl = typeof input.llmBaseUrl === 'string' ? input.llmBaseUrl : ''
  const llmApiKey = typeof input.llmApiKey === 'string' ? input.llmApiKey : ''
  const llmModel = typeof input.llmModel === 'string' ? input.llmModel : ''
  const rawTemp = input.temperature
  const temperature = Number.isFinite(rawTemp) ? Number(rawTemp) : 0.2
  return {
    llmBaseUrl,
    llmApiKey,
    llmModel,
    temperature,
  }
}

const api = {
  saveSettings: (payload) => ipcRenderer.invoke('save-settings', sanitizeSettings(payload)),
  loadSettings: () => ipcRenderer.invoke('load-settings'),
  getPort: () => ipcRenderer.invoke('get-port'),
  onBackendStatus: (listener) => {
    const wrapped = (_event, payload) => listener(payload)
    ipcRenderer.on('backend-status', wrapped)
    return () => ipcRenderer.removeListener('backend-status', wrapped)
  },
}

contextBridge.exposeInMainWorld('api', api)
