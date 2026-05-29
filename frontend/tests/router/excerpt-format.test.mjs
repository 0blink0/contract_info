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
  assert.match(code, /export function excerptTablePreview/)
  assert.match(code, /export function verificationExcerptTeaser/)
  assert.match(code, /export function excerptSummaryRowspans/)
  assert.match(code, /export function listTableRowKey/)
})

test('excerpt summary rowspans merge list-table rows', async () => {
  const { excerptSummaryRowspans, listTableRowKey } = await import(
    '../../src/utils/excerptFormat.ts'
  )
  assert.equal(listTableRowKey('fee_rates[0].运营费类型'), 'fee_rates[0]')
  const rows = [
    {
      field: 'fee_rates[0].基金名称',
      excerpt: 'same',
      excerpt_table: { rows: [['a']] },
    },
    {
      field: 'fee_rates[0].运营费类型',
      excerpt: 'same',
      excerpt_table: { rows: [['a']] },
    },
    {
      field: 'fee_rates[1].运营费类型',
      excerpt: 'other',
      excerpt_table: { rows: [['b']] },
    },
  ]
  assert.deepEqual(excerptSummaryRowspans(rows), [2, 0, 1])
})
