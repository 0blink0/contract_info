<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPathB, downloadBlob } from '@/api/client'
import type { PathBResponse } from '@/api/types'
import { labelForPathBSnippet } from '@/utils/pathBLabels'

const props = defineProps<{
  jobId: string | null
  available: boolean
  visible: boolean
}>()

const loaded = ref(false)
const loading = ref(false)
const data = ref<PathBResponse | null>(null)
const activeNames = ref<string[]>([])
const showJson = ref(false)

watch(
  () => props.jobId,
  () => {
    loaded.value = false
    loading.value = false
    data.value = null
    activeNames.value = []
    showJson.value = false
  },
)

const crmRows = computed(() => data.value?.crm_handoff ?? [])

const snippetRows = computed(() => {
  const pb = data.value
  if (!pb) return []
  const labelOf = (path: string) => labelForPathBSnippet(path, pb)
  if (pb.source_snippet_rows?.length) {
    return pb.source_snippet_rows.map((r) => ({
      path: r.path,
      label: r.label || labelOf(r.path),
      text: r.text,
    }))
  }
  const snippets = pb.source_snippets
  if (!snippets) return []
  return Object.entries(snippets).map(([path, text]) => ({
    path,
    label: labelOf(path),
    text,
  }))
})

const tierRows = computed(() => {
  const tiers = data.value?.performance_fee?.tiers
  return Array.isArray(tiers) ? tiers : []
})

const coverageLabel = (c: string) => {
  if (c === 'full') return '可直接填'
  if (c === 'partial') return '建议核对'
  return '需手录'
}

const coverageTagType = (c: string) => {
  if (c === 'full') return 'success'
  if (c === 'partial') return 'warning'
  return 'info'
}

const filledCount = computed(() =>
  crmRows.value.filter((r) => r.suggested_value && r.coverage !== 'missing').length,
)

const jsonText = computed(() =>
  data.value ? JSON.stringify(data.value, null, 2) : '',
)

async function load() {
  if (!props.jobId || loaded.value) return
  loading.value = true
  try {
    data.value = await getPathB(props.jobId)
    loaded.value = true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '路径 B 加载失败')
  } finally {
    loading.value = false
  }
}

async function onExpand(names: string | string[]) {
  const open = Array.isArray(names) ? names.length > 0 : Boolean(names)
  if (open && props.available) await load()
}

async function refresh() {
  if (!props.jobId) return
  loaded.value = false
  await load()
}

const downloading = ref(false)
async function downloadReport() {
  if (!props.jobId) return
  downloading.value = true
  try {
    await downloadBlob(props.jobId, 'review-report', '核对报告.xlsx')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '下载失败')
  } finally {
    downloading.value = false
  }
}

async function copyJson() {
  if (!jsonText.value) return
  try {
    await navigator.clipboard.writeText(jsonText.value)
    ElMessage.success('已复制 JSON')
  } catch {
    ElMessage.error('复制失败')
  }
}

function downloadJson() {
  if (!props.jobId || !jsonText.value) return
  const blob = new Blob([jsonText.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `path_b_${props.jobId}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div v-if="visible" class="path-b-panel">
    <el-collapse v-model="activeNames" @change="onExpand">
      <el-collapse-item name="pathb">
        <template #title>
          <span class="panel-title">路径 B（需 CRM 手录）</span>
          <el-text type="info" size="small" class="panel-hint">
            业绩报酬 / 开放日 — 不进 Excel 导入母版
          </el-text>
        </template>
        <el-empty v-if="!available" description="暂无路径 B 数据" />
        <template v-else>
          <div class="actions">
            <el-button size="small" :loading="loading" @click="refresh">刷新</el-button>
            <el-button
              size="small"
              type="primary"
              :loading="downloading"
              :disabled="!available"
              @click="downloadReport"
            >
              下载核对报告 (.xlsx)
            </el-button>
            <el-button size="small" :disabled="!data" @click="showJson = !showJson">
              {{ showJson ? '隐藏 JSON' : '查看 JSON' }}
            </el-button>
            <el-button size="small" :disabled="!data" @click="copyJson">复制 JSON</el-button>
            <el-button size="small" :disabled="!data" @click="downloadJson">下载原始 JSON</el-button>
          </div>
          <el-skeleton v-if="loading && !data" :rows="4" animated />
          <template v-else-if="data">
            <p v-if="data.open_day?.fixed_schedule" class="field-line">
              <strong>固定开放日：</strong>{{ data.open_day.fixed_schedule }}
            </p>
            <p class="summary-line">
              CRM 业绩报酬设置：已建议
              <strong>{{ filledCount }}</strong>
              / 6 项（对照图二「业绩报酬提取设置」手录）
            </p>
            <el-table
              v-if="tierRows.length"
              :data="tierRows"
              size="small"
              stripe
              border
              class="section-table"
              empty-text="无业绩报酬档位"
            >
              <el-table-column prop="share_class" label="份额" width="80" />
              <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
              <el-table-column prop="ratio_pct" label="比例%" width="90" />
            </el-table>
            <el-table
              :data="crmRows"
              size="small"
              stripe
              border
              class="section-table"
              empty-text="暂无 CRM 字段建议"
            >
              <el-table-column prop="crm_field" label="CRM 字段" width="150" />
              <el-table-column label="建议填写" min-width="180">
                <template #default="{ row }">
                  <span v-if="row.suggested_value">{{ row.suggested_value }}</span>
                  <el-text v-else type="info">— 未从合同推断 —</el-text>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="coverageTagType(row.coverage)" size="small">
                    {{ coverageLabel(row.coverage) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="diagnostic" label="诊断说明" min-width="180" show-overflow-tooltip />
              <el-table-column prop="snippet" label="合同摘录" min-width="240" show-overflow-tooltip />
            </el-table>
            <div v-if="snippetRows.length" class="snippets">
              <div class="sub-title">合同摘录（按字段）</div>
              <el-table :data="snippetRows" size="small" stripe border max-height="240">
                <el-table-column prop="label" label="字段" width="220" show-overflow-tooltip />
                <el-table-column prop="text" label="摘录" min-width="280" show-overflow-tooltip />
              </el-table>
            </div>
            <pre v-if="showJson" class="json-block">{{ jsonText }}</pre>
          </template>
        </template>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.path-b-panel {
  margin-bottom: 12px;
}
.panel-title {
  font-weight: 600;
  margin-right: 8px;
}
.panel-hint {
  margin-left: 4px;
}
.actions {
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.section-table {
  margin-bottom: 12px;
}
.field-line {
  margin: 0 0 8px;
  font-size: 13px;
}
.summary-line {
  margin: 0 0 10px;
  font-size: 13px;
  color: #606266;
}
.snippets {
  margin-bottom: 12px;
}
.sub-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.json-block {
  margin-top: 12px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
