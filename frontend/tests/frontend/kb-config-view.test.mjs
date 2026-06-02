import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', '..', '..')
const viewPath = path.join(root, 'frontend', 'src', 'views', 'KbConfigView.vue')
const viewCode = fs.readFileSync(viewPath, 'utf-8')

test('kb config view includes core columns and pagination', () => {
  assert.match(viewCode, /label="字段名"/)
  assert.match(viewCode, /label="字段值"/)
  assert.match(viewCode, /label="原文摘录"/)
  assert.match(viewCode, /label="来源合同"/)
  assert.match(viewCode, /label="入库时间"/)
  assert.match(viewCode, /<el-pagination/)
})
