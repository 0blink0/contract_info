import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const read = (p) => fs.readFileSync(path.join(root, p), 'utf-8')

const hubCode = read('frontend/src/views/JobHubView.vue')
const layoutCode = read('frontend/src/layouts/JobDetailLayout.vue')
const fieldBCode = read('frontend/src/views/JobFieldBView.vue')

test('JobHubView has summary, warnings, and validation', () => {
  assert.match(hubCode, /useHubSummary/)
  assert.match(hubCode, /HubSectionCard/)
  assert.match(hubCode, /WarningsList/)
  assert.match(hubCode, /ValidationPanel/)
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
