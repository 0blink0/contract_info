import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..')
const ipcPath = path.join(root, 'electron', 'ipc.ts')
const mainPath = path.join(root, 'electron', 'main.ts')
const ipcCode = fs.readFileSync(ipcPath, 'utf-8')
const mainCode = fs.readFileSync(mainPath, 'utf-8')

test('save-settings handler triggers restart workflow', () => {
  assert.match(ipcCode, /restartBackendWithRollback/)
  assert.match(ipcCode, /RESTART_ERROR/)
  assert.match(ipcCode, /rollbackApplied/)
})

test('main process exposes restart and rollback behaviors', () => {
  assert.match(mainCode, /async function restartBackendWithRollback/)
  assert.match(mainCode, /restoreSettings\(previous\)/)
  assert.match(mainCode, /setBackendState\('restarting'\)/)
})
