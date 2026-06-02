import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const viewPath = path.join(root, 'frontend', 'src', 'views', 'KbConfigView.vue')
const composablePath = path.join(root, 'frontend', 'src', 'composables', 'useKbConfigList.ts')
const viewCode = fs.readFileSync(viewPath, 'utf-8')
const composableCode = fs.readFileSync(composablePath, 'utf-8')

test('delete confirmation copy is present', () => {
  assert.match(viewCode, /删除后不可恢复/)
})

test('delete refreshes with current context', () => {
  assert.match(composableCode, /await deleteKbEntry\(id\)/)
  assert.match(composableCode, /await refresh\(\)/)
})
