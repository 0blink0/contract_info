<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getJobPreview } from '@/api/client'
import type { JobPreview } from '@/api/types'

const props = defineProps<{
  jobId: string | null
  status: string
}>()

const PREVIEW_STATUSES = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

const loading = ref(false)
const preview = ref<JobPreview | null>(null)
const activeTab = ref('product')

async function loadPreview() {
  if (!props.jobId || !PREVIEW_STATUSES.has(props.status)) {
    preview.value = null
    return
  }
  loading.value = true
  try {
    preview.value = await getJobPreview(props.jobId)
  } catch (e) {
    preview.value = null
    if (props.status === 'exported' || props.status === 'extracted') {
      ElMessage.warning(e instanceof Error ? e.message : '预览加载失败')
    }
  } finally {
    loading.value = false
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
    <div class="preview-title">导出内容预览</div>
    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else-if="preview">
      <el-text type="info" size="small" class="source-hint">
        数据来源：{{ preview.source === 'xlsx' ? '已生成 Excel' : '抽取结果' }}
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
            <el-table-column prop="value" label="值" min-width="240" show-overflow-tooltip />
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
              v-for="col in preview.fee_columns.length
                ? preview.fee_columns
                : preview.fee_rows.length
                  ? Object.keys(preview.fee_rows[0])
                  : []"
              :key="col"
              :prop="col"
              :label="col"
              min-width="120"
              show-overflow-tooltip
            />
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
.preview-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.source-hint {
  display: block;
  margin-bottom: 8px;
}
.preview-tabs {
  margin-top: 4px;
}
</style>
