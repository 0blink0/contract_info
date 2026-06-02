import { reactive, readonly } from 'vue'
import type { AppSettings } from '../../../electron/types/ipc'

type BootstrapState = 'idle' | 'starting' | 'healthy' | 'restarting' | 'failed' | 'stopped'

interface BootstrapStoreState {
  backendState: BootstrapState
  backendPort: number | null
  configReady: boolean
  onboardingStep: number
  onboardingDraft: AppSettings
  onboardingCompleted: boolean
  error: string | null
}

const ONBOARDING_STEP_KEY = 'ctrx.onboarding.step'
const ONBOARDING_DRAFT_KEY = 'ctrx.onboarding.draft'
const ONBOARDING_DONE_KEY = 'ctrx.onboarding.done'

const EMPTY_SETTINGS: AppSettings = {
  llmBaseUrl: '',
  llmApiKey: '',
  llmModel: '',
  temperature: 0.2,
  ragTopK: 3,
}

function normalizeRagTopK(value: unknown): number {
  const candidate = Number(value ?? 3)
  return Number.isInteger(candidate) && candidate >= 1 && candidate <= 10 ? candidate : 3
}

function readSavedStep(): number {
  const raw = globalThis.localStorage?.getItem(ONBOARDING_STEP_KEY)
  const parsed = Number(raw ?? '0')
  if (!Number.isFinite(parsed)) return 0
  return Math.max(0, Math.min(2, parsed))
}

function readSavedDraft(): AppSettings {
  const raw = globalThis.localStorage?.getItem(ONBOARDING_DRAFT_KEY)
  if (!raw) return { ...EMPTY_SETTINGS }
  try {
    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return {
      ...EMPTY_SETTINGS,
      ...parsed,
    }
  } catch {
    return { ...EMPTY_SETTINGS }
  }
}

function readSavedDone(): boolean {
  return globalThis.localStorage?.getItem(ONBOARDING_DONE_KEY) === 'true'
}

const state = reactive<BootstrapStoreState>({
  backendState: 'idle',
  backendPort: null,
  configReady: false,
  onboardingStep: readSavedStep(),
  onboardingDraft: readSavedDraft(),
  onboardingCompleted: readSavedDone(),
  error: null,
})

export async function bootstrapDesktopApp(): Promise<void> {
  state.backendState = 'starting'
  state.error = null

  if (!window.api) {
    state.backendState = 'failed'
    state.error = 'Electron API bridge is unavailable'
    return
  }

  const [portRes, configRes] = await Promise.all([window.api.getPort(), window.api.loadSettings()])
  if (!portRes.ok) {
    state.backendState = 'failed'
    state.error = portRes.error?.message ?? 'Failed to resolve backend port'
    return
  }
  if (!configRes.ok) {
    state.backendState = 'failed'
    state.error = configRes.error?.message ?? 'Failed to load settings'
    return
  }

  state.backendPort = portRes.data.port
  state.configReady = Boolean(configRes.data.llmBaseUrl && configRes.data.llmApiKey && configRes.data.llmModel)
  const normalizedSettings: AppSettings = {
    ...configRes.data,
    ragTopK: normalizeRagTopK(configRes.data.ragTopK),
  }
  state.onboardingDraft = {
    ...state.onboardingDraft,
    ...normalizedSettings,
  }
  state.onboardingCompleted = readSavedDone()
  state.backendState = 'healthy'
}

export function shouldRequireOnboarding(): boolean {
  return !(state.configReady && state.onboardingCompleted)
}

export function updateOnboardingDraft(next: AppSettings): void {
  state.onboardingDraft = {
    ...state.onboardingDraft,
    ...next,
  }
  globalThis.localStorage?.setItem(ONBOARDING_DRAFT_KEY, JSON.stringify(state.onboardingDraft))
}

export function setOnboardingStep(step: number): void {
  const normalized = Math.max(0, Math.min(2, step))
  state.onboardingStep = normalized
  globalThis.localStorage?.setItem(ONBOARDING_STEP_KEY, String(normalized))
}

export function completeOnboarding(finalSettings: AppSettings): void {
  state.configReady = true
  state.onboardingCompleted = true
  state.onboardingDraft = {
    ...state.onboardingDraft,
    ...finalSettings,
  }
  state.onboardingStep = 2
  globalThis.localStorage?.setItem(ONBOARDING_DONE_KEY, 'true')
  globalThis.localStorage?.setItem(ONBOARDING_STEP_KEY, '2')
  globalThis.localStorage?.setItem(ONBOARDING_DRAFT_KEY, JSON.stringify(state.onboardingDraft))
}

export function resetOnboardingCompletion(): void {
  state.onboardingCompleted = false
  globalThis.localStorage?.setItem(ONBOARDING_DONE_KEY, 'false')
}

export function markConfigReady(ready: boolean): void {
  state.configReady = ready
}

/** Desktop (file://) must call the spawned backend by port; dev/Docker use relative /api/v1. */
export function getApiBase(): string {
  if (typeof window !== 'undefined' && window.api) {
    const port = state.backendPort ?? 8765
    return `http://127.0.0.1:${port}/api/v1`
  }
  return '/api/v1'
}

export function useAppBootstrapStore() {
  return {
    state: readonly(state),
  }
}
