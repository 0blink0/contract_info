<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { TableVerificationResponse, VerificationRow } from '@/api/types'
import { getTableVerification } from '@/api/client'
import type { TableKey } from '@/constants/jobSections'
import {
  allExcerptTables,
  excerptSummaryRowspans,
  formatExcerptParagraphs,
  listTableRowKey,
  verificationExcerptTeaser,
} from '@/utils/excerptFormat'

const props = defineProps<{
  jobId: string
  tableKey: TableKey
  status: string
}>()

const PREVIEW_STATUSES = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

const loading = ref(false)
const data = ref<TableVerificationResponse | null>(null)
const selectedField = ref<string | null>(null)

const selectedRow = computed(() => {
  const rows = data.value?.rows ?? []
  if (!rows.length) return null
  if (selectedField.value) {
    const hit = rows.find((r) => r.field === selectedField.value)
    if (hit) return hit
  }
  return (
    rows.find(
      (r) => allExcerptTables(r).length > 0 || r.excerpt?.trim(),
    ) ?? rows[0]
  )
})

const excerptParagraphs = computed(() =>
  formatExcerptParagraphs(selectedRow.value?.excerpt),
)

const excerptTableBlocks = computed(() =>
  allExcerptTables(selectedRow.value ?? {}).filter((t) => t.rows?.length),
)

const excerptSummarySpans = computed(() =>
  excerptSummaryRowspans(data.value?.rows ?? []),
)

/** Column index of「摘录摘要」— shifts when validation column visible. */
const excerptColumnIndex = computed(() =>
  data.value?.rows?.some((r) => r.validation_status) ? 3 : 2,
)

function excerptSpanMethod({
  rowIndex,
  columnIndex,
}: {
  rowIndex: number
  columnIndex: number
}): { rowspan: number; colspan: number } {
  if (columnIndex !== excerptColumnIndex.value) {
    return { rowspan: 1, colspan: 1 }
  }
  const span = excerptSummarySpans.value[rowIndex] ?? 1
  return span === 0 ? { rowspan: 0, colspan: 0 } : { rowspan: span, colspan: 1 }
}

function excerptSummaryForRow(row: VerificationRow, rowIndex: number): string {
  const span = excerptSummarySpans.value[rowIndex] ?? 1
  if (span === 0) return ''
  return verificationExcerptTeaser(row)
}

function tableColCount(rows: string[][]): number {
  return Math.max(0, ...rows.map((r) => r.length))
}

function tableHeader(rows: string[][]): string[] | null {
  return rows.length > 1 ? rows[0] : null
}

function tableBody(rows: string[][]): string[][] {
  if (rows.length <= 1) return rows
  return rows.slice(1)
}

function padTableRow(row: string[], colCount: number): string[] {
  const out = [...row]
  while (out.length < colCount) out.push('')
  return out
}

const CAPTURE_LABELS: Record<string, string> = {
  rule: '规则抓取原文',
  llm: '模型摘录',
  snippet: '合同摘录',
  block: '段落原文',
  table: '合同表格原文',
  narrative: '费用章节叙述',
  'table+narrative': '表格 + 费用章节',
  value: '字段对应原文',
}

const excerptKindLabel = computed(() => {
  const src = selectedRow.value?.capture_source
  if (!src) return '合同原文摘录'
  return CAPTURE_LABELS[src] ?? '合同原文摘录'
})

const listTableGroupLabel = computed(() => {
  const field = selectedRow.value?.field
  if (!field) return ''
  const key = listTableRowKey(field)
  if (!key) return ''
  const rows = data.value?.rows ?? []
  const sameGroup = rows.filter((r) => listTableRowKey(r.field) === key)
  return sameGroup.length > 1 ? key : ''
})

function valueSummary(value: string | null | undefined, maxLen = 72): string {
  const raw = value?.trim()
  if (!raw) return '—'
  const oneLine = raw.replace(/\s+/g, ' ')
  if (oneLine.length <= maxLen) return oneLine
  return `${oneLine.slice(0, maxLen)}…`
}

function rowClassName({ row }: { row: VerificationRow }) {
  return row.field === selectedRow.value?.field ? 'row-active' : ''
}

function selectRow(row: VerificationRow) {
  selectedField.value = row.field
}

function pickDefaultRow(rows: VerificationRow[]) {
  const withExcerpt = rows.find(
    (r) => allExcerptTables(r).length > 0 || r.excerpt?.trim(),
  )
  selectedField.value = (withExcerpt ?? rows[0])?.field ?? null
}

async function load() {
  if (!PREVIEW_STATUSES.has(props.status)) {
    data.value = null
    selectedField.value = null
    return
  }
  loading.value = true
  try {
    data.value = await getTableVerification(props.jobId, props.tableKey)
    if (data.value?.rows?.length) {
      pickDefaultRow(data.value.rows)
    } else {
      selectedField.value = null
    }
  } catch (e) {
    data.value = null
    selectedField.value = null
    ElMessage.warning(e instanceof Error ? e.message : '核对数据加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.jobId, props.tableKey, props.status] as const,
  () => void load(),
  { immediate: true },
)
</script>

<template>
  <div class="verification-table">
    <div class="verification-header">
      <h4 class="verification-title">摘录核对</h4>
      <el-text type="info" size="small">
        点击左侧行阅读完整摘录；同一运营费行等多字段共用一条摘要
      </el-text>
    </div>

    <el-skeleton v-if="loading" :rows="3" animated />

    <div v-else-if="data?.rows?.length" class="verification-layout">
      <div class="verification-main">
        <el-table
          :data="data.rows"
          size="small"
          stripe
          border
          highlight-current-row
          max-height="560"
          :row-class-name="rowClassName"
          :span-method="excerptSpanMethod"
          @row-click="selectRow"
        >
          <el-table-column
            prop="field_label"
            label="字段"
            min-width="120"
            show-overflow-tooltip
          />
          <el-table-column label="字段值" min-width="100" show-overflow-tooltip>
            <template #default="{ row }">{{ row.value ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="摘录摘要" min-width="160">
            <template #default="{ row, $index }">
              <span
                v-if="(excerptSummarySpans[$index] ?? 1) > 0"
                class="excerpt-teaser"
                :class="{
                  'excerpt-teaser--empty':
                    !row.excerpt?.trim() && allExcerptTables(row).length === 0,
                }"
              >
                {{ excerptSummaryForRow(row, $index) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            v-if="data.rows.some((r) => r.validation_status)"
            label="校验"
            width="88"
          >
            <template #default="{ row }">
              <el-tag
                v-if="row.validation_status"
                size="small"
                :type="row.validation_status === 'fail' ? 'danger' : 'warning'"
              >
                {{ row.validation_status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <aside class="excerpt-reader" aria-label="原文摘录阅读区">
        <div v-if="selectedRow" class="excerpt-reader-inner">
          <div class="excerpt-reader-head">
            <div class="excerpt-reader-head-top">
              <h5 class="excerpt-reader-title">
                {{ selectedRow.field_label }}
                <span
                  v-if="listTableGroupLabel"
                  class="excerpt-group-hint"
                >（本组字段共用此摘录）</span>
              </h5>
              <el-tag
                v-if="selectedRow.capture_source === 'rule'"
                size="small"
                type="info"
                effect="plain"
              >
                规则抓取
              </el-tag>
            </div>
            <p v-if="selectedRow.value" class="excerpt-value" :title="selectedRow.value">
              <span class="excerpt-value-label">字段值</span>
              {{ valueSummary(selectedRow.value) }}
            </p>
            <p class="excerpt-body-label">{{ excerptKindLabel }}</p>
          </div>
          <div
            v-if="excerptTableBlocks.length || excerptParagraphs.length"
            class="excerpt-body"
          >
            <div
              v-for="(block, bi) in excerptTableBlocks"
              :key="`tbl-${bi}`"
              class="excerpt-table-block"
            >
              <p v-if="block.caption" class="excerpt-table-caption">
                {{ block.caption }}
              </p>
              <table class="contract-source-table">
                <thead v-if="tableHeader(block.rows!)">
                  <tr>
                    <th
                      v-for="(cell, ci) in padTableRow(
                        tableHeader(block.rows!)!,
                        tableColCount(block.rows!),
                      )"
                      :key="`h-${bi}-${ci}`"
                    >
                      {{ cell || ' ' }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, ri) in tableBody(block.rows!)"
                    :key="`r-${bi}-${ri}`"
                  >
                    <td
                      v-for="(cell, ci) in padTableRow(
                        row,
                        tableColCount(block.rows!),
                      )"
                      :key="`c-${bi}-${ri}-${ci}`"
                    >
                      {{ cell || ' ' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p
              v-for="(para, idx) in excerptParagraphs"
              :key="`p-${idx}`"
              class="excerpt-para"
            >
              {{ para }}
            </p>
          </div>
          <el-empty v-else description="该字段暂无原文摘录" :image-size="48" />
        </div>
        <el-empty v-else description="请选择左侧字段" :image-size="48" />
      </aside>
    </div>

    <el-empty
      v-else
      description="暂无摘录核对数据（需完成抽取；仅导出 Excel 时无合同原文摘录）"
      :image-size="64"
    />
  </div>
</template>

<style scoped>
.verification-table {
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--app-border);
}

.verification-header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
  margin-bottom: 12px;
}

.verification-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.verification-layout {
  display: grid;
  grid-template-columns: minmax(260px, 0.85fr) minmax(440px, 1.25fr);
  gap: 16px;
  align-items: stretch;
  min-height: 420px;
}

.verification-main {
  min-width: 0;
}

.excerpt-reader {
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--app-surface, #fff);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius, 12px);
  box-shadow: var(--app-shadow);
  overflow: hidden;
}

.excerpt-reader-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
  max-height: min(72vh, 640px);
}

.excerpt-reader-head {
  flex-shrink: 0;
  padding: 12px 14px;
  border-bottom: 1px solid var(--app-border);
  background: #f8fafc;
}

.excerpt-reader-head-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.excerpt-reader-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.4;
}

.excerpt-group-hint {
  font-size: 12px;
  font-weight: 400;
  color: #64748b;
}

.excerpt-value {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.55;
  color: #64748b;
}

.excerpt-value-label {
  color: #94a3b8;
  margin-right: 6px;
}

.excerpt-body-label {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.excerpt-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
}

.excerpt-para {
  margin: 0 0 1em;
  font-size: 13px;
  line-height: 1.75;
  color: #334155;
  text-align: justify;
  word-break: break-word;
}

.excerpt-para:last-child {
  margin-bottom: 0;
}

.excerpt-table-block {
  margin-bottom: 1.25em;
  overflow-x: auto;
}

.excerpt-table-caption {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.contract-source-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  line-height: 1.5;
}

.contract-source-table th,
.contract-source-table td {
  border: 1px solid #e2e8f0;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
  word-break: break-word;
  color: #334155;
}

.contract-source-table th {
  background: #f1f5f9;
  font-weight: 600;
  color: #0f172a;
}

.contract-source-table tbody tr:nth-child(even) {
  background: #f8fafc;
}

.excerpt-teaser {
  font-size: 12px;
  color: #475569;
  cursor: pointer;
}

.excerpt-teaser--empty {
  color: #94a3b8;
}

:deep(.row-active) {
  background-color: var(--app-primary-soft, #eff6ff) !important;
}

:deep(.el-table__row) {
  cursor: pointer;
}

@media (max-width: 960px) {
  .verification-layout {
    grid-template-columns: 1fr;
  }

  .excerpt-reader-inner {
    max-height: 480px;
  }
}
</style>
