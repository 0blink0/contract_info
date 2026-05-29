import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..')
const mainPath = path.join(root, 'electron', 'main.ts')
const mainCode = fs.readFileSync(mainPath, 'utf-8')

test('main process uses backend binary spawn contract', () => {
  assert.match(mainCode, /spawn\(entry,\s*\[\]/)
  assert.match(mainCode, /ctrx-backend\.exe/)
  assert.match(mainCode, /backend-manifest\.json/)
})

test('main process includes health poll and retry settings', () => {
  assert.match(mainCode, /HEALTH_INTERVAL_MS\s*=\s*300/)
  assert.match(mainCode, /HEALTH_TIMEOUT_MS\s*=\s*30_000/)
  assert.match(mainCode, /RETRY_BACKOFF_MS\s*=\s*\[0,\s*2000,\s*5000\]/)
})

test('main process loads renderer before backend bootstrap chain', () => {
  assert.match(mainCode, /loadRenderer\(mainWindow\)/)
  assert.match(mainCode, /loadURL\(/)
  assert.match(mainCode, /loadFile\(/)
})

test('splash screen is shipped beside main bundle', () => {
  const splashPath = path.join(root, 'electron', 'splash.html')
  assert.ok(fs.existsSync(splashPath), 'electron/splash.html must exist')
  const splash = fs.readFileSync(splashPath, 'utf-8')
  assert.match(splash, /正在启动本地服务/)
  assert.match(mainCode, /loadSplash\(/)
  assert.match(mainCode, /splash\.html/)
})
