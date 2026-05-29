import { app, BrowserWindow, dialog } from 'electron'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { registerIpcHandlers } from './ipc.ts'
import { loadSettings, restoreSettings } from './store.ts'
import type { AppSettings } from './types/ipc.ts'

type BackendState = 'idle' | 'starting' | 'healthy' | 'restarting' | 'failed' | 'stopped'

interface BackendRuntimeError {
  summary: string
  logPath: string
}

const HEALTH_PATH = '/api/v1/health'
const HEALTH_TIMEOUT_MS = 30_000
const HEALTH_INTERVAL_MS = 300
const RETRY_BACKOFF_MS = [0, 2000, 5000]
const MAX_RETRIES = 3
const DEFAULT_PORT = 8765
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let mainWindow: BrowserWindow | null = null
let backendState: BackendState = 'idle'
let backendProcess: ChildProcessWithoutNullStreams | null = null
let retryAttempt = 0
let lastError: BackendRuntimeError | null = null
let quitting = false
let manualRetryRequested = false

function setBackendState(next: BackendState): void {
  backendState = next
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('backend-status', { state: backendState })
  }
}

function backendLogPath(): string {
  return path.join(app.getPath('userData'), 'logs', 'backend.log')
}

function backendEntrypoint(): string {
  const resourcesCandidates = [
    path.join(__dirname, 'resources'),
    path.join(app.getAppPath(), 'electron', 'resources'),
    path.join(process.resourcesPath, 'electron', 'resources'),
  ]
  const resourcesDir =
    resourcesCandidates.find((candidate) => fs.existsSync(path.join(candidate, '.backend-manifest.json'))) ??
    resourcesCandidates[0]
  const manifestPath = path.join(resourcesDir, '.backend-manifest.json')
  const fallback = process.platform === 'win32'
    ? path.join(resourcesDir, 'ctrx-backend-win-x64-v1.2.0', 'ctrx-backend.exe')
    : path.join(resourcesDir, 'ctrx-backend-linux-x64-v1.2.0', 'ctrx-backend')

  try {
    const raw = fs.readFileSync(manifestPath, 'utf-8')
    const manifest = JSON.parse(raw) as {
      current?: { path?: string }
    }
    const relDir = manifest.current?.path
    if (!relDir) return fallback
    const exe = process.platform === 'win32' ? 'ctrx-backend.exe' : 'ctrx-backend'
    return path.join(resourcesDir, relDir, exe)
  } catch {
    return fallback
  }
}

async function waitForHealth(port: number): Promise<void> {
  const startedAt = Date.now()
  while (Date.now() - startedAt < HEALTH_TIMEOUT_MS) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}${HEALTH_PATH}`)
      if (response.ok) return
    } catch {
      // polling until timeout
    }
    await new Promise((resolve) => setTimeout(resolve, HEALTH_INTERVAL_MS))
  }
  throw new Error('Backend health check timed out after 30 seconds')
}

function attachBackendListeners(port: number): void {
  if (!backendProcess) return
  const logPath = backendLogPath()

  backendProcess.once('exit', (code, signal) => {
    if (quitting || manualRetryRequested) return
    if (backendState === 'healthy' || backendState === 'starting' || backendState === 'restarting') {
      lastError = {
        summary: `Backend exited unexpectedly (code=${code ?? 'null'}, signal=${signal ?? 'null'})`,
        logPath,
      }
      void scheduleRestart(port)
    }
  })

  backendProcess.stderr.on('data', (chunk) => {
    lastError = {
      summary: String(chunk).trim().slice(0, 300),
      logPath,
    }
  })
}

function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  return {
    ...process.env,
    CTRX_PORT: String(port),
    CTRX_DATA_DIR: app.getPath('userData'),
    OPENAI_API_KEY: settings.llmApiKey.trim(),
    OPENAI_BASE_URL: settings.llmBaseUrl.trim(),
    LLM_MODEL: settings.llmModel.trim(),
  }
}

async function spawnBackend(port: number): Promise<void> {
  setBackendState(retryAttempt > 0 ? 'restarting' : 'starting')
  const entry = backendEntrypoint()
  backendProcess = spawn(entry, [], {
    env: backendChildEnv(port),
  })
  attachBackendListeners(port)
  await waitForHealth(port)
  retryAttempt = 0
  setBackendState('healthy')
}

async function scheduleRestart(port: number): Promise<void> {
  if (retryAttempt >= MAX_RETRIES) {
    setBackendState('failed')
    await showFatalDialog()
    return
  }

  const delay = RETRY_BACKOFF_MS[Math.min(retryAttempt, RETRY_BACKOFF_MS.length - 1)]
  retryAttempt += 1
  await new Promise((resolve) => setTimeout(resolve, delay))
  await spawnBackend(port).catch(async (error: unknown) => {
    lastError = {
      summary: error instanceof Error ? error.message : 'Unknown restart error',
      logPath: backendLogPath(),
    }
    await scheduleRestart(port)
  })
}

async function stopBackend(): Promise<void> {
  if (!backendProcess) {
    setBackendState('stopped')
    return
  }

  const child = backendProcess
  backendProcess = null
  child.kill('SIGTERM')

  const exited = await new Promise<boolean>((resolve) => {
    let settled = false
    const timeoutId = setTimeout(() => {
      if (settled) return
      settled = true
      resolve(false)
    }, 5000)
    child.once('exit', () => {
      if (settled) return
      settled = true
      clearTimeout(timeoutId)
      resolve(true)
    })
  })

  if (!exited) child.kill('SIGKILL')
  setBackendState('stopped')
}

async function restartBackendWithRollback(previous: AppSettings): Promise<{
  restarted: boolean
  rollbackApplied: boolean
  logPath: string
}> {
  const port = DEFAULT_PORT
  setBackendState('restarting')
  try {
    await stopBackend()
    retryAttempt = 0
    await spawnBackend(port)
    return {
      restarted: true,
      rollbackApplied: false,
      logPath: backendLogPath(),
    }
  } catch (restartError) {
    lastError = {
      summary: restartError instanceof Error ? restartError.message : 'restart failed',
      logPath: backendLogPath(),
    }
    restoreSettings(previous)
    try {
      await stopBackend()
      retryAttempt = 0
      await spawnBackend(port)
      return {
        restarted: false,
        rollbackApplied: true,
        logPath: backendLogPath(),
      }
    } catch (rollbackError) {
      lastError = {
        summary: rollbackError instanceof Error ? rollbackError.message : 'rollback restart failed',
        logPath: backendLogPath(),
      }
      setBackendState('failed')
      throw new Error(`settings restart/rollback failed: ${lastError.summary}; log=${lastError.logPath}`)
    }
  }
}

async function showFatalDialog(): Promise<void> {
  const detail = [
    `日志路径: ${lastError?.logPath ?? backendLogPath()}`,
    `最近错误: ${lastError?.summary ?? 'unknown error'}`,
    '你可以点击“重试”重新拉起后端进程。',
  ].join('\n')

  const result = await dialog.showMessageBox({
    type: 'error',
    title: '后端启动失败',
    message: '后端连续重试 3 次后仍失败',
    detail,
    buttons: ['退出应用', '重试'],
    defaultId: 1,
    cancelId: 0,
  })

  if (result.response === 1) {
    manualRetryRequested = true
    retryAttempt = 0
    lastError = null
    manualRetryRequested = false
    await spawnBackend(DEFAULT_PORT).catch(() => {
      void scheduleRestart(DEFAULT_PORT)
    })
  }
}

function resolvePreloadPath(): string {
  for (const name of ['preload.cjs', 'preload.js']) {
    const candidate = path.join(__dirname, name)
    if (fs.existsSync(candidate)) return candidate
  }
  return path.join(__dirname, 'preload.cjs')
}

function resolveSplashPath(): string {
  return path.join(__dirname, 'splash.html')
}

function loadSplash(window: BrowserWindow): void {
  const splashPath = resolveSplashPath()
  if (fs.existsSync(splashPath)) {
    void window.loadFile(splashPath)
    return
  }
  void window.loadURL(
    'data:text/html;charset=utf-8,' +
      encodeURIComponent(
        '<html><body style="font-family:Segoe UI,Arial;padding:24px;color:#333;">CTRX 正在启动后端，请稍候...</body></html>',
      ),
  )
}

function createMainWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    show: true,
    backgroundColor: '#f4f6fb',
    webPreferences: {
      contextIsolation: true,
      preload: resolvePreloadPath(),
    },
  })

  loadSplash(window)
  return window
}

async function loadRenderer(window: BrowserWindow): Promise<void> {
  const devUrl = process.env.ELECTRON_RENDERER_URL
  if (devUrl) {
    await window.loadURL(devUrl)
    return
  }
  const indexPath = path.join(app.getAppPath(), 'frontend', 'dist', 'index.html')
  await window.loadFile(indexPath)
}

async function bootstrap(): Promise<void> {
  const port = DEFAULT_PORT
  mainWindow = createMainWindow()
  registerIpcHandlers({
    resolvePort: () => port,
    restartBackendWithRollback,
  })

  try {
    await spawnBackend(port)
    if (mainWindow && !mainWindow.isDestroyed()) {
      await loadRenderer(mainWindow)
    }
  } catch (error: unknown) {
    lastError = {
      summary: error instanceof Error ? error.message : 'Unknown startup error',
      logPath: backendLogPath(),
    }
    await scheduleRestart(port)
  }
}

app.whenReady().then(() => {
  void bootstrap()
})

app.on('before-quit', () => {
  quitting = true
  void stopBackend()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
