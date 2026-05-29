import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const read = (p) => fs.readFileSync(path.join(root, p), 'utf-8')

test('UploadView supports multi-file upload and batch run', () => {
  const code = read('frontend/src/views/UploadView.vue')
  assert.match(code, /useJobsPoll|createJobsPoll/)
  assert.match(code, /UploadJobCard/)
  assert.match(code, /multiple/)
  assert.match(code, /:limit="MAX_UPLOAD_FILES"|limit=\{MAX_UPLOAD_FILES\}/)
  assert.match(code, /全部开始处理/)
  assert.match(code, /getJobConcurrency/)
  assert.match(code, /on-exceed|onExceed/)
})

test('useJobsPoll uses shared interval polling', () => {
  const code = read('frontend/src/composables/useJobsPoll.ts')
  assert.match(code, /setInterval/)
  assert.match(code, /register/)
  assert.match(code, /activate/)
})

test('client exposes concurrency endpoint', () => {
  const code = read('frontend/src/api/client.ts')
  assert.match(code, /getJobConcurrency/)
  assert.match(code, /\/jobs\/concurrency/)
})
