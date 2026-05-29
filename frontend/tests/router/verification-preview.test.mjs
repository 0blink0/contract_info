import test from 'node:test'
import assert from 'node:assert/strict'

test('applyVerificationRowsToPreview updates fee row by field path', async () => {
  const { applyVerificationRowsToPreview } = await import(
    '../../src/constants/jobSections.ts'
  )
  const preview = {
    job_id: 'j1',
    section: 'fee-rates',
    source: 'extraction',
    fee_columns: ['运营费类型', '费率（单位：%/年）'],
    fee_rows: [
      { 运营费类型: '管理费', '费率（单位：%/年）': '1' },
    ],
  }
  const rows = [
    {
      field: 'fee_rates[0].运营费类型',
      field_label: '运营费类型',
      value: '托管费',
    },
    {
      field: 'fee_rates[0].rate_annual_pct',
      field_label: '费率（单位：%/年）',
      value: '0.05',
    },
  ]
  const out = applyVerificationRowsToPreview('fee-rates', preview, rows)
  assert.equal(out.fee_rows[0]['运营费类型'], '托管费')
  assert.equal(out.fee_rows[0]['费率（单位：%/年）'], '0.05')
})
