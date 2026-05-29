import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const read = (p) => fs.readFileSync(path.join(root, p), 'utf-8')

const hubCode = read('frontend/src/views/JobHubView.vue')
const layoutCode = read('frontend/src/layouts/JobDetailLayout.vue')
const fieldBCode = read('frontend/src/views/JobFieldBView.vue')

test('JobHubView has summary and warnings without stacked ValidationPanel', () => {
  assert.match(hubCode, /useHubSummary/)
  assert.match(hubCode, /HubSectionCard/)
  assert.match(hubCode, /WarningsList/)
  assert.doesNotMatch(hubCode, /ValidationPanel/)
  assert.match(hubCode, /validation_fail_count/)
})

test('VerificationExcerptTable shows LLM validation column', () => {
  const code = read('frontend/src/components/table/VerificationExcerptTable.vue')
  assert.match(code, /label="LLM校验"/)
  assert.match(code, /validationAvailable/)
  assert.match(code, /validation_reason/)
})

test('JobTableView passes validation availability to excerpt table', () => {
  const code = read('frontend/src/views/JobTableView.vue')
  assert.match(code, /validation-available/)
})

test('JobDetailLayout does not stack hub-only panels', () => {
  assert.doesNotMatch(layoutCode, /WarningsList/)
  assert.doesNotMatch(layoutCode, /ValidationPanel/)
  assert.doesNotMatch(layoutCode, /ExportPreview/)
  assert.doesNotMatch(layoutCode, /PathBPanel/)
})

test('JobFieldBView uses PathBDetail', () => {
  assert.match(fieldBCode, /PathBDetail/)
  assert.doesNotMatch(fieldBCode, /将在下一阶段开放/)
})
