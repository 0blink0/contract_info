import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const utilPath = path.resolve(
  import.meta.dirname,
  '..',
  '..',
  'src',
  'utils',
  'excerptFormat.ts',
)
const code = fs.readFileSync(utilPath, 'utf-8')

test('excerpt format utilities are exported', () => {
  assert.match(code, /export function formatExcerptParagraphs/)
  assert.match(code, /export function excerptPreview/)
})
