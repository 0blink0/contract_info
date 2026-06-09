<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { downloadBlob, reextractProduct, saveJobPreviewSection } from '@/api/client'
import type { VerificationRow } from '@/api/types'
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { useSectionPreview } from '@/composables/useSectionPreview'
import TablePreviewEditor from '@/components/table/TablePreviewEditor.vue'
import VerificationExcerptTable from '@/components/table/VerificationExcerptTable.vue'
import {
  applyVerificationRowsToPreview,
  buildSectionSaveBody,
  isValidTableKey,
  normalizeSectionPreview,
  sectionLabel,
  TABLE_DOWNLOAD_FILES,
  type TableKey,
} from '@/constants/jobSections'

const route = useRoute()
const { jobId, status, detail } = useJobDetailInject()

const tableKeyParam = computed(() => {
  const k = route.params.tableKey
  return typeof k === 'string' ? k : ''
})

const tableKey = computed(() =>
  isValidTableKey(tableKeyParam.value) ? (tableKeyParam.value as TableKey) : null,
)

const label = computed(() => (tableKey.value ? sectionLabel(tableKey.value) : ''))

const {
  preview,
  loading,
  canShowPreview,
  load: reloadPreview,
} = useSectionPreview(tableKeyParam)

const verificationRef = ref<{
  reload: () => Promise<void>
  finishSave: () => void
  cancelEdit: () => void
} | null>(null)
const verificationEditing = ref(false)
const verificationSaving = ref(false)

const PREVIEW_EDIT_STATUSES = new Set([
  'extracted',
  'exporting',
  'exported',
  'export_failed',
])

const canEditVerification = computed(
  () =>
    Boolean(tableKey.value && PREVIEW_EDIT_STATUSES.has(status.value)),
)

const showDownload = computed(() => detail.value?.status === 'exported')
const showReextract = computed(
  () => tableKey.value === 'product-elements' && Boolean(canShowPreview.value),
)
const reextracting = ref(false)

async function onReextract() {
  const id = jobId.value
  if (!id) return
  reextracting.value = true
  try {
    await reextractProduct(id)
    await reloadPreview()
    await verificationRef.value?.reload()
    ElMessage.success('产品要素重新抽取成功')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '重新抽取失败')
  } finally {
    reextracting.value = false
  }
}

async function onDownload() {
  const id = jobId.value
  const key = tableKey.value
  if (!id || !key) return
  try {
    await downloadBlob(id, key, TABLE_DOWNLOAD_FILES[key])
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '下载失败')
  }
}

onBeforeRouteLeave(async () => {
  if (!verificationEditing.value) return true
  try {
    await ElMessageBox.confirm(
      '摘录核对有未保存的修改，确定离开当前页面？',
      '未保存的修改',
      {
        type: 'warning',
        confirmButtonText: '离开',
        cancelButtonText: '留在此页',
      },
    )
    return true
  } catch {
    return false
  }
})

async function onVerificationSave(rows: VerificationRow[]) {
  const key = tableKey.value
  const id = jobId.value
  if (!key || !id || !preview.value) return
  verificationSaving.value = true
  try {
    const updated = applyVerificationRowsToPreview(key, preview.value, rows)
    const body = buildSectionSaveBody(key, updated)
    const data = await saveJobPreviewSection(id, key, body)
    preview.value = normalizeSectionPreview(key, data)
    verificationRef.value?.finishSave()
    await verificationRef.value?.reload()
    ElMessage.success('已保存并更新上方预览与 Excel')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    verificationSaving.value = false
  }
}
</script>

<template>
  <div v-if="tableKey && jobId" class="table-view">
    <div class="table-toolbar">
      <h3 class="section-title">{{ label }}</h3>
      <div class="toolbar-actions">
        <el-button
          v-if="showReextract"
          :loading="reextracting"
          size="default"
          @click="onReextract"
        >
          重新抽取
        </el-button>
        <el-button
          v-if="showDownload"
          type="success"
          size="default"
          @click="onDownload"
        >
          下载{{ label }}
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!canShowPreview"
      type="info"
      :closable="false"
      show-icon
      title="抽取完成后可在此编辑并核对"
      description="请先开始处理并等待任务进入 extracted 或 exported 状态。"
      class="status-alert"
    />

    <template v-else>
      <el-text type="info" size="small" class="source-hint">
        上方为数据预览；请在下方「摘录核对」中点击「编辑」对照原文修改字段值并保存。
      </el-text>

      <TablePreviewEditor
        :table-key="tableKey"
        :preview="preview"
        :can-edit="false"
        :loading="loading"
      />

      <VerificationExcerptTable
        ref="verificationRef"
        :job-id="jobId"
        :table-key="tableKey"
        :status="status"
        :validation-available="detail?.validation_available ?? false"
        :can-edit-values="canEditVerification"
        :save-loading="verificationSaving"
        @save="onVerificationSave"
        @editing-change="(v) => (verificationEditing = v)"
      />
    </template>
  </div>
</template>

<style scoped>
.table-view {
  min-height: 120px;
}

.table-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #0f172a;
  line-height: 32px;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-alert {
  margin-bottom: 16px;
}

.source-hint {
  display: block;
  margin-bottom: 12px;
}
</style>
