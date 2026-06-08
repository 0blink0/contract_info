import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const viewPath = path.join(root, 'frontend', 'src', 'views', 'SettingsView.vue')
const viewCode = fs.readFileSync(viewPath, 'utf-8')

test('settings view uses save-settings and restart feedback', () => {
  assert.match(viewCode, /saveSettings/)
  assert.match(viewCode, /window\.api\.saveSettings/)
  assert.match(viewCode, /正在重连后端|重连/)
})
