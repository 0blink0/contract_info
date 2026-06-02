import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const composablePath = path.join(root, 'frontend', 'src', 'composables', 'useKbConfigList.ts')
const composableCode = fs.readFileSync(composablePath, 'utf-8')

test('kb filter uses field_name and debounce refresh', () => {
  assert.match(composableCode, /field_name:\s*keyword\.value/)
  assert.match(composableCode, /setTimeout\(\(\)\s*=>\s*\{\s*void refresh\(\)/)
})

test('keyword change resets page to one', () => {
  assert.match(composableCode, /watch\(\s*keyword[\s\S]*page\.value = 1/)
})
