<!-- Phase 17: superseded by TablePreviewEditor + JobTableView. Kept for JobDetail.vue reference until Phase 18. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getJobPreview, saveJobPreview } from '@/api/client'
import type { JobPreview } from '@/api/types'

const props = defineProps<{
  jobId: string | null
  status: string
}>()

const PREVIEW_STATUSES = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

const loading = ref(false)
const saving = ref(false)
const dirty = ref(false)
const preview = ref<JobPreview | null>(null)
const activeTab = ref('product')

const canEdit = computed(
  () => props.status === 'extracted' || props.status === 'exported' || props.status === 'export_failed',
)

function markDirty() {
  dirty.value = true
}

function columnKeys(
  columns: string[],
  rows: Record<string, string | null>[],
): string[] {
  if (columns.length) return columns.filter((c) => c !== '摘录原文')
  if (!rows.length) return []
  return Object.keys(rows[0]).filter((c) => c !== '摘录原文')
}

const feeCols = computed(() =>
  preview.value ? columnKeys(preview.value.fee_columns, preview.value.fee_rows) : [],
)
const lockCols = computed(() =>
  preview.value ? columnKeys(preview.value.lock_columns, preview.value.lock_rows) : [],
)
const subCols = computed(() =>
  preview.value
    ? columnKeys(preview.value.subscription_columns, preview.value.subscription_rows)
    : [],
)
const shareCols = computed(() =>
  preview.value ? columnKeys(preview.value.share_columns, preview.value.share_rows) : [],
)

async function loadPreview() {
  if (!props.jobId || !PREVIEW_STATUSES.has(props.status)) {
    preview.value = null
    dirty.value = false
    return
  }
  loading.value = true
  try {
    preview.value = await getJobPreview(props.jobId)
    dirty.value = false
  } catch (e) {
    preview.value = null
    if (props.status === 'exported' || props.status === 'extracted') {
      ElMessage.warning(e instanceof Error ? e.message : '预览加载失败')
    }
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (!props.jobId || !preview.value || !canEdit.value) return
  saving.value = true
  try {
    preview.value = await saveJobPreview(props.jobId, {
      product_rows: preview.value.product_rows,
      fee_columns: preview.value.fee_columns,
      fee_rows: preview.value.fee_rows,
      lock_columns: preview.value.lock_columns,
      lock_rows: preview.value.lock_rows,
      share_columns: preview.value.share_columns,
      share_rows: preview.value.share_rows,
      subscription_columns: preview.value.subscription_columns,
      subscription_rows: preview.value.subscription_rows,
    })
    dirty.value = false
    ElMessage.success('已保存并重新生成 Excel，下载将使用最新内容')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

watch(
  () => [props.jobId, props.status] as const,
  () => void loadPreview(),
  { immediate: true },
)
</script>

<template>
  <div v-if="jobId && PREVIEW_STATUSES.has(status)" class="export-preview">
    <div class="preview-header">
      <div class="preview-title">导出内容预览（可编辑）</div>
      <el-button
        v-if="canEdit"
        type="primary"
        size="small"
        :loading="saving"
        :disabled="!dirty || !preview"
        @click="onSave"
      >
        保存修改
      </el-button>
    </div>
    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else-if="preview">
      <el-text type="info" size="small" class="source-hint">
        修改后请点击「保存修改」写入数据库并更新 Excel；绿色下载按钮将导出最新文件。
      </el-text>
      <el-tabs v-model="activeTab" class="preview-tabs">
        <el-tab-pane label="产品要素" name="product">
          <el-table
            :data="preview.product_rows"
            size="small"
            stripe
            border
            max-height="360"
            empty-text="暂无产品要素数据"
          >
            <el-table-column prop="field" label="字段" min-width="160" show-overflow-tooltip />
            <el-table-column label="值" min-width="240">
              <template #default="{ row }">
                <el-input
                  v-if="canEdit"
                  v-model="row.value"
                  size="small"
                  @input="markDirty"
                />
                <span v-else>{{ row.value }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`运营费率（${preview.fee_rows.length} 行）`" name="fee">
          <el-table
            :data="preview.fee_rows"
            size="small"
            stripe
            border
            max-height="360"
            empty-text="暂无费率数据"
          >
            <el-table-column
              v-for="col in feeCols"
              :key="col"
              :label="col"
              min-width="120"
            >
              <template #default="{ row }">
                <el-input
                  v-if="canEdit"
                  v-model="row[col]"
                  size="small"
                  @input="markDirty"
                />
                <span v-else>{{ row[col] }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`份额锁定期（${preview.lock_rows.length} 行）`" name="lock">
          <el-table
            :data="preview.lock_rows"
            size="small"
            stripe
            border
            max-height="360"
            empty-text="暂无锁定期子表数据"
          >
            <el-table-column
              v-for="col in lockCols"
              :key="col"
              :label="col"
              min-width="120"
            >
              <template #default="{ row }">
                <el-input
                  v-if="canEdit"
                  v-model="row[col]"
                  size="small"
                  @input="markDirty"
                />
                <span v-else>{{ row[col] }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane
          :label="`申赎费率（${preview.subscription_rows.length} 行）`"
          name="subscription"
        >
          <el-table
            :data="preview.subscription_rows"
            size="small"
            stripe
            border
            max-height="360"
            empty-text="暂无申赎费率数据"
          >
            <el-table-column
              v-for="col in subCols"
              :key="col"
              :label="col"
              min-width="120"
            >
              <template #default="{ row }">
                <el-input
                  v-if="canEdit"
                  v-model="row[col]"
                  size="small"
                  @input="markDirty"
                />
                <span v-else>{{ row[col] }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`分级份额（${preview.share_rows.length} 行）`" name="share">
          <el-table
            :data="preview.share_rows"
            size="small"
            stripe
            border
            max-height="360"
            empty-text="暂无分级份额数据（非分级产品可能为空）"
          >
            <el-table-column
              v-for="col in shareCols"
              :key="col"
              :label="col"
              min-width="120"
            >
              <template #default="{ row }">
                <el-input
                  v-if="canEdit"
                  v-model="row[col]"
                  size="small"
                  @input="markDirty"
                />
                <span v-else>{{ row[col] }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<style scoped>
.export-preview {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.preview-title {
  font-weight: 600;
}
.source-hint {
  display: block;
  margin-bottom: 8px;
}
.preview-tabs {
  margin-top: 4px;
}
</style>
