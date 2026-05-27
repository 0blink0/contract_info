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

watch(
  () => props.jobId,
  () => {
    loaded.value = false
    loading.value = false
    data.value = null
    activeNames.value = []
  },
)

const snippetRows = computed(() => {
  if (!data.value?.source_snippets) return []
  return Object.entries(data.value.source_snippets).map(([path, text]) => ({
    path,
    text,
  }))
})

const jsonText = computed(() =>
  data.value ? JSON.stringify(data.value, null, 2) : '',
)

const tierRows = computed(() => {
  const tiers = data.value?.performance_fee?.tiers
  return Array.isArray(tiers) ? tiers : []
})

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
            <el-button size="small" :disabled="!data" @click="copyJson">复制 JSON</el-button>
            <el-button size="small" :disabled="!data" @click="downloadJson">下载 JSON</el-button>
          </div>
          <el-skeleton v-if="loading && !data" :rows="4" animated />
          <template v-else-if="data">
            <p v-if="data.open_day?.fixed_schedule" class="field-line">
              <strong>固定开放日：</strong>{{ data.open_day.fixed_schedule }}
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
            <div v-if="snippetRows.length" class="snippets">
              <div class="sub-title">合同摘录（source_snippets）</div>
              <el-table :data="snippetRows" size="small" stripe border max-height="200">
                <el-table-column prop="path" label="字段路径" width="200" show-overflow-tooltip />
                <el-table-column prop="text" label="摘录" min-width="240" show-overflow-tooltip />
              </el-table>
            </div>
            <pre class="json-block">{{ jsonText }}</pre>
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
.sub-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.field-line {
  margin: 0 0 8px;
  font-size: 13px;
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
