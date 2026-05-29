import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const routerPath = path.join(root, 'frontend', 'src', 'router', 'index.ts')
const routerCode = fs.readFileSync(routerPath, 'utf-8')

test('router has onboarding route and gate', () => {
  assert.match(routerCode, /path:\s*['"]\/onboarding['"]/)
  assert.match(routerCode, /beforeEach\(/)
  assert.match(routerCode, /shouldRequireOnboarding/)
})
