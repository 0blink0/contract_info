<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { TableVerificationResponse, VerificationRow } from '@/api/types'
import { getTableVerification } from '@/api/client'
import type { TableKey } from '@/constants/jobSections'
import { excerptPreview, formatExcerptParagraphs } from '@/utils/excerptFormat'

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
  return rows.find((r) => r.excerpt?.trim()) ?? rows[0]
})

const excerptParagraphs = computed(() =>
  formatExcerptParagraphs(selectedRow.value?.excerpt),
)

function rowClassName({ row }: { row: VerificationRow }) {
  return row.field === selectedRow.value?.field ? 'row-active' : ''
}

function selectRow(row: VerificationRow) {
  selectedField.value = row.field
}

function pickDefaultRow(rows: VerificationRow[]) {
  const withExcerpt = rows.find((r) => r.excerpt?.trim())
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
        点击左侧行，在右侧阅读完整原文摘录
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
          max-height="420"
          :row-class-name="rowClassName"
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
            <template #default="{ row }">
              <span
                class="excerpt-teaser"
                :class="{ 'excerpt-teaser--empty': !row.excerpt?.trim() }"
              >
                {{ excerptPreview(row.excerpt) }}
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
            <h5 class="excerpt-reader-title">{{ selectedRow.field_label }}</h5>
            <el-text v-if="selectedRow.value" type="info" size="small" class="excerpt-value">
              字段值：{{ selectedRow.value }}
            </el-text>
          </div>
          <div v-if="excerptParagraphs.length" class="excerpt-body">
            <p
              v-for="(para, idx) in excerptParagraphs"
              :key="idx"
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
  display: flex;
  gap: 16px;
  align-items: stretch;
  min-height: 280px;
}

.verification-main {
  flex: 1;
  min-width: 0;
}

.excerpt-reader {
  width: min(380px, 38vw);
  flex-shrink: 0;
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
  min-height: 280px;
  max-height: 420px;
}

.excerpt-reader-head {
  flex-shrink: 0;
  padding: 12px 14px;
  border-bottom: 1px solid var(--app-border);
  background: #f8fafc;
}

.excerpt-reader-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.4;
}

.excerpt-value {
  display: block;
  line-height: 1.5;
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
    flex-direction: column;
  }

  .excerpt-reader {
    width: 100%;
    max-height: 320px;
  }
}
</style>
