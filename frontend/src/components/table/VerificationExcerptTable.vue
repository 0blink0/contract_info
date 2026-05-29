<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { TableVerificationResponse, VerificationRow } from '@/api/types'
import { getTableVerification } from '@/api/client'
import type { TableKey } from '@/constants/jobSections'

const props = defineProps<{
  jobId: string
  tableKey: TableKey
  status: string
}>()

const PREVIEW_STATUSES = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

const loading = ref(false)
const data = ref<TableVerificationResponse | null>(null)

function pageDisplay(row: VerificationRow): string {
  if (row.page_no != null) return String(row.page_no)
  if (row.page_no_note) return row.page_no_note
  return '—'
}

async function load() {
  if (!PREVIEW_STATUSES.has(props.status)) {
    data.value = null
    return
  }
  loading.value = true
  try {
    data.value = await getTableVerification(props.jobId, props.tableKey)
  } catch (e) {
    data.value = null
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
      <el-text v-if="data && !data.page_no_available" type="info" size="small">
        页码暂未解析，以下页码列仅供参考或为空
      </el-text>
    </div>
    <el-skeleton v-if="loading" :rows="3" animated />
    <el-table
      v-else-if="data?.rows?.length"
      :data="data.rows"
      size="small"
      stripe
      border
      max-height="360"
    >
      <el-table-column prop="field_label" label="字段" min-width="140" show-overflow-tooltip />
      <el-table-column label="字段值" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.value ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="摘录页码" width="120">
        <template #default="{ row }">{{ pageDisplay(row) }}</template>
      </el-table-column>
      <el-table-column label="原文摘录" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.excerpt ?? '—' }}</template>
      </el-table-column>
      <el-table-column
        v-if="data.rows.some((r) => r.validation_status)"
        label="校验"
        width="100"
      >
        <template #default="{ row }">
          <el-tag v-if="row.validation_status" size="small" :type="row.validation_status === 'fail' ? 'danger' : 'warning'">
            {{ row.validation_status }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无摘录核对数据（需完成抽取；仅导出 Excel 时无合同原文摘录）" :image-size="64" />
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
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}

.verification-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}
</style>
