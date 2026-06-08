import type { AppSettings, GetPortData, IpcResult, SaveSettingsData } from '../../../../electron/types/ipc'

interface DesktopApi {
  saveSettings: (payload: AppSettings) => Promise<IpcResult<SaveSettingsData>>
  loadSettings: () => Promise<IpcResult<AppSettings>>
  getPort: () => Promise<IpcResult<GetPortData>>
  onBackendStatus: (listener: (payload: { state: string }) => void) => () => void
}

declare global {
  interface Window {
    api?: DesktopApi
  }
}

export {}
