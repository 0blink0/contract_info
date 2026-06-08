import { ipcMain } from 'electron'
import { getSettingsFilePath, loadSettings, restoreSettings, saveSettings } from './store.ts'
import type { AppSettings, GetPortData, IpcResult, SaveSettingsData } from './types/ipc.ts'

function ok<T>(data: T): IpcResult<T> {
  return { ok: true, data, error: null }
}

function fail<T>(message: string, code = 'IPC_ERROR', fallbackData: T): IpcResult<T> {
  return {
    ok: false,
    data: fallbackData,
    error: {
      code,
      message,
    },
  }
}

interface RegisterIpcOptions {
  resolvePort: () => number
  restartBackendWithRollback: (previous: AppSettings) => Promise<{ restarted: boolean; rollbackApplied: boolean; logPath: string }>
}

export function registerIpcHandlers(options: RegisterIpcOptions): void {
  ipcMain.handle('save-settings', async (_event, payload: AppSettings): Promise<IpcResult<SaveSettingsData>> => {
    const previous = loadSettings()
    const result = saveSettings(payload)
    if (!result.ok) {
      return fail(result.reason, 'VALIDATION_ERROR', {
        filePath: getSettingsFilePath(),
        restarted: false,
        rollbackApplied: false,
        logPath: '',
      })
    }
    try {
      const restartResult = await options.restartBackendWithRollback(previous)
      return ok({
        filePath: getSettingsFilePath(),
        ...restartResult,
      })
    } catch (error) {
      restoreSettings(previous)
      return fail(
        error instanceof Error ? error.message : 'restart failed',
        'RESTART_ERROR',
        {
          filePath: getSettingsFilePath(),
          restarted: false,
          rollbackApplied: true,
          logPath: '',
        },
      )
    }
  })

  ipcMain.handle('load-settings', async (): Promise<IpcResult<AppSettings>> => {
    try {
      return ok(loadSettings())
    } catch (error) {
      return fail(error instanceof Error ? error.message : 'load failed', 'LOAD_ERROR', {
        llmBaseUrl: '',
        llmApiKey: '',
        llmModel: '',
        temperature: 0.2,
      })
    }
  })

  ipcMain.handle('get-port', async (): Promise<IpcResult<GetPortData>> => {
    try {
      return ok({ port: options.resolvePort() })
    } catch (error) {
      return fail(error instanceof Error ? error.message : 'get-port failed', 'PORT_ERROR', { port: 8765 })
    }
  })
}
