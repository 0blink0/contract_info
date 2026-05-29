import test from 'node:test'
import assert from 'node:assert/strict'

// Minimal runtime check: slice helper is exported from jobSections (used by client fallback).
const { createRequire } = await import('node:module')
const require = createRequire(import.meta.url)
const path = new URL('../../src/constants/jobSections.ts', import.meta.url)

test('jobSections exports slicePreviewSection for legacy API fallback', async () => {
  const code = await import('node:fs').then((fs) =>
    fs.readFileSync(path, 'utf-8'),
  )
  assert.match(code, /export function slicePreviewSection/)
  assert.match(code, /export function mergeSectionIntoFullPreview/)
})
