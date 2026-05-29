import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const routerPath = path.join(root, 'frontend', 'src', 'router', 'index.ts')
const sectionsPath = path.join(root, 'frontend', 'src', 'constants', 'jobSections.ts')
const layoutPath = path.join(root, 'frontend', 'src', 'layouts', 'JobDetailLayout.vue')
const hubPath = path.join(root, 'frontend', 'src', 'views', 'JobHubView.vue')
const tablePath = path.join(root, 'frontend', 'src', 'views', 'JobTableView.vue')
const fieldBPath = path.join(root, 'frontend', 'src', 'views', 'JobFieldBView.vue')

const routerCode = fs.readFileSync(routerPath, 'utf-8')
const sectionsCode = fs.readFileSync(sectionsPath, 'utf-8')
const layoutCode = fs.readFileSync(layoutPath, 'utf-8')
const hubCode = fs.readFileSync(hubPath, 'utf-8')
const tableCode = fs.readFileSync(tablePath, 'utf-8')
const fieldBCode = fs.readFileSync(fieldBPath, 'utf-8')

test('nested job routes use JobDetailLayout and child names', () => {
  assert.match(routerCode, /JobDetailLayout\.vue/)
  assert.match(routerCode, /name:\s*['"]job-hub['"]/)
  assert.match(routerCode, /name:\s*['"]job-table['"]/)
  assert.match(routerCode, /name:\s*['"]job-field-b['"]/)
  assert.match(routerCode, /tables\/:tableKey/)
  assert.match(routerCode, /field-b/)
  assert.match(routerCode, /isValidTableKey/)
  assert.doesNotMatch(routerCode, /name:\s*['"]job-detail['"]/)
  assert.doesNotMatch(routerCode, /JobDetailView\.vue/)
})

test('jobSections exports backend-aligned table keys', () => {
  assert.match(sectionsCode, /product-elements/)
  assert.match(sectionsCode, /subscription-fee-rates/)
  assert.match(sectionsCode, /isValidTableKey/)
})

test('JobDetailLayout back button returns to hub on child routes', () => {
  assert.match(layoutCode, /isHubRoute/)
  assert.match(layoutCode, /返回文件详情/)
  assert.match(layoutCode, /返回文件列表/)
  assert.match(layoutCode, /name:\s*['"]job-hub['"]/)
  assert.match(layoutCode, /function onBack/)
})

test('JobDetailLayout shows status and downloads only on hub route', () => {
  assert.match(layoutCode, /v-if="isHubRoute"/)
  assert.match(layoutCode, /child-shell--page/)
})

test('JobTableView has section title and per-table download beside save', () => {
  assert.match(tableCode, /section-title/)
  assert.match(tableCode, /下载\{\{ label \}\}/)
  assert.match(tableCode, /toolbar-actions/)
})

test('only JobDetailLayout uses useJobPoll among layout and child views', () => {
  assert.match(layoutCode, /useJobPoll/)
  assert.doesNotMatch(hubCode, /useJobPoll/)
  assert.doesNotMatch(tableCode, /useJobPoll/)
  assert.doesNotMatch(fieldBCode, /useJobPoll/)
})

test('child views use job detail inject', () => {
  assert.match(hubCode, /useJobDetailInject/)
  assert.match(tableCode, /useJobDetailInject/)
  assert.match(fieldBCode, /useJobDetailInject/)
})

test('JobTableView uses sectional preview not job poll', () => {
  assert.match(tableCode, /useSectionPreview/)
  assert.doesNotMatch(tableCode, /useJobPoll/)
  assert.match(tableCode, /onBeforeRouteLeave/)
})
