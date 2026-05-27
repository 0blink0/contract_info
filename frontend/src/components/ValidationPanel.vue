<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getValidation } from '@/api/client'
import type { ValidationItem, ValidationResponse } from '@/api/types'

const props = defineProps<{
  jobId: string | null
  visible: boolean
  failCount: number
  warnCount: number
  available: boolean
}>()

const loaded = ref(false)
const loading = ref(false)
const data = ref<ValidationResponse | null>(null)
const showPass = ref(false)

const displayItems = computed(() => {
  const items = data.value?.items ?? []
  if (showPass.value) return items
  return items.filter((i) => i.status === 'fail' || i.status === 'warn')
})

const failN = computed(() => data.value?.summary?.fail ?? props.failCount)
const warnN = computed(() => data.value?.summary?.warn ?? props.warnCount)

function rowClassName({ row }: { row: ValidationItem }) {
  if (row.status === 'fail') return 'row-fail'
  if (row.status === 'warn') return 'row-warn'
  if (row.status === 'pass') return 'row-pass'
  return ''
}

function statusTagType(status: string) {
  if (status === 'fail') return 'danger'
  if (status === 'warn') return 'warning'
  if (status === 'pass') return 'success'
  return 'info'
}

async function load() {
  if (!props.jobId || loaded.value) return
  loading.value = true
  try {
    data.value = await getValidation(props.jobId)
    loaded.value = true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '校验结果加载失败')
  } finally {
    loading.value = false
  }
}

async function onExpand(names: string | string[]) {
  const open = Array.isArray(names) ? names.length > 0 : Boolean(names)
  if (open) await load()
}

async function refresh() {
  if (!props.jobId) return
  loaded.value = false
  await load()
}
</script>

<template>
  <div v-if="visible" class="validation-panel">
    <el-collapse @change="onExpand">
      <el-collapse-item name="validation">
        <template #title>
          <span class="panel-title">摘录一致性校验（LLM）</span>
          <el-tag v-if="failN > 0" type="danger" size="small" class="badge">fail {{ failN }}</el-tag>
          <el-tag v-if="warnN > 0" type="warning" size="small" class="badge">warn {{ warnN }}</el-tag>
        </template>
        <el-alert
          v-if="failN > 0"
          type="warning"
          :closable="false"
          show-icon
          class="advisory"
          title="存在与合同摘录不一致的字段，请复核后再导入 CRM；仍可下载 Excel。"
        />
        <el-empty
          v-if="!available && !loading"
          description="暂无校验结果（可能未配置 LLM）"
        />
        <template v-else>
          <div class="toolbar">
            <el-switch v-model="showPass" active-text="显示 pass" inactive-text="仅 fail/warn" />
            <el-button size="small" :loading="loading" @click="refresh">刷新</el-button>
          </div>
          <el-skeleton v-if="loading && !data" :rows="3" animated />
          <template v-else-if="data?.skipped">
            <el-text type="info">已跳过 LLM 校验（未配置 API Key）</el-text>
          </template>
          <el-table
            v-else-if="data"
            :data="displayItems"
            size="small"
            stripe
            border
            max-height="360"
            :row-class-name="rowClassName"
            empty-text="无 fail/warn 项"
          >
            <el-table-column label="字段" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span :title="row.field">{{ row.field_label || row.field }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="value" label="值" width="120" show-overflow-tooltip />
            <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
            <el-table-column prop="suggestion" label="建议" min-width="100" show-overflow-tooltip />
            <el-table-column
              prop="evidence_text"
              label="摘录原文"
              min-width="220"
              show-overflow-tooltip
            />
          </el-table>
        </template>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.validation-panel {
  margin-bottom: 12px;
}
.panel-title {
  font-weight: 600;
  margin-right: 8px;
}
.badge {
  margin-left: 6px;
}
.advisory {
  margin-bottom: 8px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
:deep(.row-fail) {
  --el-table-tr-bg-color: #fef0f0;
}
:deep(.row-warn) {
  --el-table-tr-bg-color: #fdf6ec;
}
:deep(.row-pass) {
  --el-table-tr-bg-color: #f0f9eb;
}
</style>
