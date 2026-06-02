import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..')
const storePath = path.join(root, 'electron', 'store.ts')
const storeCode = fs.readFileSync(storePath, 'utf-8')

test('settings default includes ragTopK=3', () => {
  assert.match(storeCode, /ragTopK:\s*3/)
})

test('validateSettings rejects ragTopK outside 1-10', () => {
  assert.match(storeCode, /Number\.isInteger\(input\.ragTopK\)/)
  assert.match(storeCode, /input\.ragTopK\s*<\s*1\s*\|\|\s*input\.ragTopK\s*>\s*10/)
})
