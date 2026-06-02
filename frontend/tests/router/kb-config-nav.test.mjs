import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const routerPath = path.join(root, 'frontend', 'src', 'router', 'index.ts')
const layoutPath = path.join(root, 'frontend', 'src', 'layouts', 'AppLayout.vue')
const routerCode = fs.readFileSync(routerPath, 'utf-8')
const layoutCode = fs.readFileSync(layoutPath, 'utf-8')

test('router and menu include /kb-config entry', () => {
  assert.match(routerCode, /path:\s*['"]\/kb-config['"]/)
  assert.match(layoutCode, /index="\/kb-config"/)
})

test('kb-config menu is between jobs and settings', () => {
  const jobsIdx = layoutCode.indexOf('index="/jobs"')
  const kbIdx = layoutCode.indexOf('index="/kb-config"')
  const settingsIdx = layoutCode.indexOf('index="/settings"')
  assert.ok(jobsIdx >= 0)
  assert.ok(kbIdx > jobsIdx)
  assert.ok(settingsIdx > kbIdx)
})
