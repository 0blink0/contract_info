import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const formPath = path.join(root, 'frontend', 'src', 'components', 'LlmConfigForm.vue')
const formCode = fs.readFileSync(formPath, 'utf-8')

test('llm config form includes required fields', () => {
  assert.match(formCode, /llmBaseUrl/)
  assert.match(formCode, /llmApiKey/)
  assert.match(formCode, /llmModel/)
  assert.match(formCode, /ragTopK/)
})

test('rag top-k input uses 1-10 integer constraints', () => {
  assert.match(formCode, /label="RAG Top-K"/)
  assert.match(formCode, /v-model="form\.ragTopK"/)
  assert.match(formCode, /:min="1"/)
  assert.match(formCode, /:max="10"/)
  assert.match(formCode, /:step="1"/)
})

test('rag top-k defaults and validation checks are present', () => {
  const settingsViewPath = path.join(root, 'frontend', 'src', 'views', 'SettingsView.vue')
  const settingsViewCode = fs.readFileSync(settingsViewPath, 'utf-8')
  const bootstrapPath = path.join(root, 'frontend', 'src', 'stores', 'appBootstrap.ts')
  const bootstrapCode = fs.readFileSync(bootstrapPath, 'utf-8')

  assert.match(formCode, /Number\.isInteger\(ragTopK\)\s*\|\|\s*ragTopK < 1\s*\|\|\s*ragTopK > 10/)
  assert.match(settingsViewCode, /ragTopK:\s*3/)
  assert.match(settingsViewCode, /ragTopK:\s*\(\(\)\s*=>/)
  assert.match(bootstrapCode, /ragTopK:\s*3/)
  assert.match(bootstrapCode, /function normalizeRagTopK/)
})

test('save payload includes ragTopK with restart flow preserved', () => {
  const settingsViewPath = path.join(root, 'frontend', 'src', 'views', 'SettingsView.vue')
  const settingsViewCode = fs.readFileSync(settingsViewPath, 'utf-8')

  assert.match(settingsViewCode, /window\.api\.saveSettings\(payload\)/)
  assert.match(settingsViewCode, /ragTopK:/)
  assert.match(settingsViewCode, /保存并重启/)
})
