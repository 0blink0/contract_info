import { app, BrowserWindow, dialog, powerMonitor } from 'electron'
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
const HEALTH_TIMEOUT_MS = 360_000
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
let keepaliveTimer: ReturnType<typeof setInterval> | null = null

function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController()
  const tid = setTimeout(() => controller.abort(), timeoutMs)
  return fetch(url, { signal: controller.signal }).finally(() => clearTimeout(tid))
}

function startKeepalive(port: number): void {
  if (keepaliveTimer) return
  let failCount = 0
  keepaliveTimer = setInterval(() => {
    if (quitting) return
    fetchWithTimeout(`http://127.0.0.1:${port}${HEALTH_PATH}`, 10_000)
      .then(() => { failCount = 0 })
      .catch(() => {
        failCount += 1
        if (failCount >= 2 && backendState === 'healthy') {
          failCount = 0
          void scheduleRestart(port)
        }
      })
  }, 30_000)
}

function stopKeepalive(): void {
  if (keepaliveTimer) {
    clearInterval(keepaliveTimer)
    keepaliveTimer = null
  }
}

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
    const raw = fs.readFileSync(manifestPath, 'utf-8').replace(/^﻿/, '')
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

function openBackendLog(): fs.WriteStream | null {
  try {
    const logPath = backendLogPath()
    fs.mkdirSync(path.dirname(logPath), { recursive: true })
    return fs.createWriteStream(logPath, { flags: 'a' })
  } catch {
    return null
  }
}

let _backendLogStream: fs.WriteStream | null = null

function writeBackendLog(line: string): void {
  const ts = new Date().toISOString()
  const entry = `[${ts}] ${line}\n`
  process.stdout.write(entry)
  _backendLogStream?.write(entry)
}

function attachBackendListeners(port: number): void {
  if (!backendProcess) return
  const logPath = backendLogPath()

  if (!_backendLogStream) {
    _backendLogStream = openBackendLog()
    writeBackendLog(`--- backend started (pid=${backendProcess.pid ?? '?'}) ---`)
  }

  backendProcess.stdout.on('data', (chunk) => {
    String(chunk).split('\n').filter(Boolean).forEach((l) => writeBackendLog(`[stdout] ${l}`))
  })

  backendProcess.stderr.on('data', (chunk) => {
    const text = String(chunk).trim()
    lastError = {
      summary: text.slice(-300),
      logPath,
    }
    text.split('\n').filter(Boolean).forEach((l) => writeBackendLog(`[stderr] ${l}`))
  })

  backendProcess.once('exit', (code, signal) => {
    writeBackendLog(`--- backend exited (code=${code ?? 'null'}, signal=${signal ?? 'null'}) ---`)
    if (quitting || manualRetryRequested) return
    if (backendState === 'healthy' || backendState === 'starting' || backendState === 'restarting') {
      lastError = {
        summary: `Backend exited unexpectedly (code=${code ?? 'null'}, signal=${signal ?? 'null'})`,
        logPath,
      }
      void scheduleRestart(port)
    }
  })
}

function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  const ragTopK = Number.isInteger(settings.ragTopK) ? settings.ragTopK : 3

  // Derive resourcesDir using same three-candidate logic as backendEntrypoint()
  const resourcesCandidates = [
    path.join(__dirname, 'resources'),
    path.join(app.getAppPath(), 'electron', 'resources'),
    path.join(process.resourcesPath, 'electron', 'resources'),
  ]
  const resourcesDir =
    resourcesCandidates.find((candidate) => fs.existsSync(path.join(candidate, '.backend-manifest.json'))) ??
    resourcesCandidates[0]
  const modelsDir = path.join(resourcesDir, 'models')

  return {
    ...process.env,           // spread FIRST — explicit keys below override system env (D-12)
    CTRX_PORT: String(port),
    CTRX_DATA_DIR: app.getPath('userData'),
    OPENAI_API_KEY: settings.llmApiKey.trim(),
    OPENAI_BASE_URL: settings.llmBaseUrl.trim(),
    LLM_MODEL: settings.llmModel.trim(),
    RAG_TOP_K: String(ragTopK),
    // Phase 23 additions (D-09)
    CTRX_MODELS_DIR: modelsDir,
    SENTENCE_TRANSFORMERS_HOME: modelsDir,
    TRANSFORMERS_CACHE: modelsDir,
  }
}

function resolvePythonBackendDev(): { command: string; args: string[]; cwd: string } | null {
  if (app.isPackaged || process.env.CTRX_USE_BACKEND_EXE === '1') return null
  const appRoot = app.getAppPath()
  const desktopMain = path.join(appRoot, 'desktop_main.py')
  if (!fs.existsSync(desktopMain)) return null
  const python = (process.env.CTRX_PYTHON ?? 'python').trim() || 'python'
  return { command: python, args: [desktopMain], cwd: appRoot }
}

function backendLaunchSpec(): { command: string; args: string[]; cwd?: string; label: string } {
  const python = resolvePythonBackendDev()
  if (python) {
    return { ...python, label: `${python.command} ${python.args.join(' ')}` }
  }
  const entry = backendEntrypoint()
  return { command: entry, args: [], label: entry }
}

function formatSpawnError(err: unknown, spec: { label: string }): string {
  const msg = err instanceof Error ? err.message : String(err)
  if (msg.includes('UNKNOWN') || msg.includes('ENOENT')) {
    return [
      `无法启动后端 (${msg})`,
      `路径: ${spec.label}`,
      '常见原因: Windows Device Guard / 应用程序控制策略拦截未签名的 ctrx-backend.exe。',
      '开发环境: 关闭 CTRX_USE_BACKEND_EXE 后 Electron 会自动改用 python desktop_main.py。',
      '安装包环境: 需 IT 放行该 exe，或为安装包配置代码签名。',
    ].join('\n')
  }
  return `spawn failed (${msg}) — ${spec.label}`
}

async function spawnBackend(port: number): Promise<void> {
  setBackendState(retryAttempt > 0 ? 'restarting' : 'starting')
  const spec = backendLaunchSpec()
  console.log('[CTRX] spawnBackend entry:', spec.label)
  if (!resolvePythonBackendDev() && !fs.existsSync(spec.command)) {
    throw new Error(`Backend executable not found: ${spec.command}`)
  }

  await new Promise<void>((resolve, reject) => {
    backendProcess = spawn(spec.command, spec.args, {
      env: backendChildEnv(port),
      cwd: spec.cwd,
    })
    backendProcess.once('error', (err) => {
      lastError = {
        summary: formatSpawnError(err, spec),
        logPath: backendLogPath(),
      }
      reject(err)
    })
    attachBackendListeners(port)
    void waitForHealth(port)
      .then(resolve)
      .catch(reject)
  })

  retryAttempt = 0
  setBackendState('healthy')
  startKeepalive(port)
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
  stopKeepalive()
  if (!backendProcess) {
    setBackendState('stopped')
    return
  }

  const child = backendProcess
  backendProcess = null
  setBackendState('stopped')  // must precede kill so exit-listener won't trigger scheduleRestart
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
  // state already set to 'stopped' before kill; no-op here
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

  // D-08: fast-fail if model directory is absent (KB-PKG-02)
  const bootstrapResourcesCandidates = [
    path.join(__dirname, 'resources'),
    path.join(app.getAppPath(), 'electron', 'resources'),
    path.join(process.resourcesPath, 'electron', 'resources'),
  ]
  const bootstrapResourcesDir =
    bootstrapResourcesCandidates.find((candidate) =>
      fs.existsSync(path.join(candidate, '.backend-manifest.json'))
    ) ?? bootstrapResourcesCandidates[0]
  const bgem3Path = path.join(bootstrapResourcesDir, 'models', 'bge-m3')
  if (!fs.existsSync(bgem3Path)) {
    lastError = {
      summary: `模型目录缺失: ${bgem3Path} — 请重新安装应用以恢复模型权重`,
      logPath: backendLogPath(),
    }
    setBackendState('failed')
    await showFatalDialog()
    return
  }

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

  // 系统从睡眠/休眠唤醒后，检查后端是否还在响应；若无响应则触发重启
  powerMonitor.on('resume', () => {
    if (quitting) return
    // 睡眠期间后端可能已崩溃；无论当前状态都做一次探测
    if (backendState === 'failed') return
    fetchWithTimeout(`http://127.0.0.1:${DEFAULT_PORT}${HEALTH_PATH}`, 10_000)
      .catch(() => {
        if (!quitting && backendState !== 'failed') {
          void scheduleRestart(DEFAULT_PORT)
        }
      })
  })
})

app.on('before-quit', () => {
  quitting = true
  void stopBackend()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
