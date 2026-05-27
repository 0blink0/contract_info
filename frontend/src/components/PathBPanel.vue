<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPathB } from '@/api/client'
import type { PathBResponse } from '@/api/types'

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
            <el-button size="small" :disabled="!data" @click="showJson = !showJson">
              {{ showJson ? '隐藏 JSON' : '查看 JSON' }}
            </el-button>
            <el-button size="small" :disabled="!data" @click="copyJson">复制 JSON</el-button>
            <el-button size="small" :disabled="!data" @click="downloadJson">下载 JSON</el-button>
          </div>
          <el-skeleton v-if="loading && !data" :rows="4" animated />
          <template v-else-if="data">
            <p class="summary-line">
              CRM 业绩报酬设置：已建议
              <strong>{{ filledCount }}</strong>
              / 6 项（对照图二「业绩报酬提取设置」手录）
            </p>
            <el-table
              :data="crmRows"
              size="small"
              stripe
              border
              class="section-table"
              empty-text="暂无 CRM 字段建议"
            >
              <el-table-column prop="crm_field" label="CRM 字段" width="160" />
              <el-table-column label="建议填写" min-width="200">
                <template #default="{ row }">
                  <span v-if="row.suggested_value">{{ row.suggested_value }}</span>
                  <el-text v-else type="info">— 未从合同推断 —</el-text>
                </template>
              </el-table-column>
              <el-table-column label="置信" width="100">
                <template #default="{ row }">
                  <el-tag :type="coverageTagType(row.coverage)" size="small">
                    {{ coverageLabel(row.coverage) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="snippet" label="合同摘录" min-width="280" show-overflow-tooltip />
            </el-table>
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
.summary-line {
  margin: 0 0 10px;
  font-size: 13px;
  color: #606266;
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
