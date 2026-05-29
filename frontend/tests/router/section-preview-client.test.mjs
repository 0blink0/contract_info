import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const clientPath = path.join(root, 'frontend', 'src', 'api', 'client.ts')
const clientCode = fs.readFileSync(clientPath, 'utf-8')

test('client exposes sectional preview and verification APIs', () => {
  assert.match(clientCode, /getJobPreviewSection/)
  assert.match(clientCode, /saveJobPreviewSection/)
  assert.match(clientCode, /getTableVerification/)
  assert.match(clientCode, /\/preview\/\$\{section\}/)
  assert.match(clientCode, /\/verification\/\$\{tableKey\}/)
})

test('sectional preview falls back to full preview on 404', () => {
  assert.match(clientCode, /isNotFoundError/)
  assert.match(clientCode, /slicePreviewSection/)
  assert.match(clientCode, /getJobPreview\(jobId\)/)
})
