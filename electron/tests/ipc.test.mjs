import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..')
const ipcPath = path.join(root, 'electron', 'ipc.ts')
const preloadPath = path.join(root, 'electron', 'preload.ts')
const ipcCode = fs.readFileSync(ipcPath, 'utf-8')
const preloadCode = fs.readFileSync(preloadPath, 'utf-8')

test('ipc handlers expose required channels', () => {
  assert.match(ipcCode, /'save-settings'/)
  assert.match(ipcCode, /'load-settings'/)
  assert.match(ipcCode, /'get-port'/)
})

test('preload exposes only narrow bridge methods', () => {
  assert.match(preloadCode, /saveSettings:/)
  assert.match(preloadCode, /loadSettings:/)
  assert.match(preloadCode, /getPort:/)
  assert.doesNotMatch(preloadCode, /exposeInMainWorld\(['"]ipcRenderer['"]/)
})
