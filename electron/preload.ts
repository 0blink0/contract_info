import { contextBridge, ipcRenderer } from 'electron'
import type { AppSettings, GetPortData, IpcResult, SaveSettingsData } from './types/ipc.ts'

export interface DesktopApi {
  saveSettings: (payload: AppSettings) => Promise<IpcResult<SaveSettingsData>>
  loadSettings: () => Promise<IpcResult<AppSettings>>
  getPort: () => Promise<IpcResult<GetPortData>>
  onBackendStatus: (listener: (payload: { state: string }) => void) => () => void
}

function sanitizeSettings(payload: AppSettings): AppSettings {
  return {
    llmBaseUrl: typeof payload?.llmBaseUrl === 'string' ? payload.llmBaseUrl : '',
    llmApiKey: typeof payload?.llmApiKey === 'string' ? payload.llmApiKey : '',
    llmModel: typeof payload?.llmModel === 'string' ? payload.llmModel : '',
    temperature: Number.isFinite(payload?.temperature) ? Number(payload.temperature) : 0.2,
  }
}

const api: DesktopApi = {
  saveSettings: (payload) => ipcRenderer.invoke('save-settings', sanitizeSettings(payload)),
  loadSettings: () => ipcRenderer.invoke('load-settings'),
  getPort: () => ipcRenderer.invoke('get-port'),
  onBackendStatus: (listener) => {
    const wrapped = (_event: unknown, payload: { state: string }) => listener(payload)
    ipcRenderer.on('backend-status', wrapped)
    return () => {
      ipcRenderer.removeListener('backend-status', wrapped)
    }
  },
}

contextBridge.exposeInMainWorld('api', api)
