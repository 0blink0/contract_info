export interface IpcError {
  code: string
  message: string
}

export interface IpcResult<T> {
  ok: boolean
  data: T
  error: IpcError | null
}

export interface LlmSettings {
  llmBaseUrl: string
  llmApiKey: string
  llmModel: string
}

export interface AppSettings extends LlmSettings {
  temperature?: number
  ragTopK?: number
}

export interface GetPortData {
  port: number
}

export interface SaveSettingsData {
  filePath: string
  restarted: boolean
  rollbackApplied: boolean
  logPath: string
}
