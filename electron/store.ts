import { app } from 'electron'
import Store from 'electron-store'
import type { AppSettings } from './types/ipc.ts'

interface StoreShape {
  settings: AppSettings
}

const DEFAULT_SETTINGS: AppSettings = {
  llmBaseUrl: '',
  llmApiKey: '',
  llmModel: '',
  temperature: 0.2,
  ragTopK: 3,
}

const store = new Store<StoreShape>({
  cwd: app.getPath('userData'),
  name: 'config',
  defaults: {
    settings: DEFAULT_SETTINGS,
  },
})

export function sanitizeApiKey(value: string): string {
  if (!value) return ''
  if (value.length <= 6) return '***'
  return `${value.slice(0, 3)}***${value.slice(-3)}`
}

export function validateSettings(input: AppSettings): string | null {
  try {
    // eslint-disable-next-line no-new
    new URL(input.llmBaseUrl)
  } catch {
    return 'llmBaseUrl must be a valid URL'
  }
  if (!input.llmApiKey?.trim()) return 'llmApiKey is required'
  if (!input.llmModel?.trim()) return 'llmModel is required'
  const topK = input.ragTopK ?? 3
  if (!Number.isInteger(topK) || topK < 1 || topK > 10) return 'ragTopK must be an integer between 1 and 10'
  return null
}

export function loadSettings(): AppSettings {
  const loaded = store.get('settings') ?? DEFAULT_SETTINGS
  return {
    ...DEFAULT_SETTINGS,
    ...loaded,
  }
}

export function saveSettings(next: AppSettings): { ok: true } | { ok: false; reason: string } {
  const withDefaults: AppSettings = { ...DEFAULT_SETTINGS, ...next }
  const validationError = validateSettings(withDefaults)
  if (validationError) return { ok: false, reason: validationError }

  const current = loadSettings()
  try {
    store.set('settings', withDefaults)
    // only masked value can appear in logs
    console.info('[settings] save ok', {
      llmBaseUrl: next.llmBaseUrl,
      llmApiKey: sanitizeApiKey(next.llmApiKey),
      llmModel: next.llmModel,
    })
    return { ok: true }
  } catch (error) {
    store.set('settings', current)
    return { ok: false, reason: error instanceof Error ? error.message : 'save failed' }
  }
}

export function snapshotSettings(): AppSettings {
  return loadSettings()
}

export function restoreSettings(snapshot: AppSettings): void {
  store.set('settings', snapshot)
}

export function getSettingsFilePath(): string {
  return store.path
}
