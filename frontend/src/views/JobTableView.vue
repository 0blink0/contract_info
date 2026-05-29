<script setup lang="ts">
import { computed } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { useSectionPreview } from '@/composables/useSectionPreview'
import TablePreviewEditor from '@/components/table/TablePreviewEditor.vue'
import VerificationExcerptTable from '@/components/table/VerificationExcerptTable.vue'
import { isValidTableKey, sectionLabel, type TableKey } from '@/constants/jobSections'

const route = useRoute()
const { jobId, status } = useJobDetailInject()

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
  saving,
  dirty,
  canEdit,
  canShowPreview,
  markDirty,
  save,
} = useSectionPreview(tableKeyParam)

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm(
      '有未保存的修改，确定离开当前页面？',
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
</script>

<template>
  <div v-if="tableKey && jobId" class="table-view">
    <div class="table-toolbar">
      <h3 class="section-title">{{ label }}</h3>
      <el-button
        v-if="canEdit"
        type="primary"
        size="small"
        :loading="saving"
        :disabled="!dirty || !preview"
        @click="save"
      >
        保存修改
      </el-button>
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
        修改后请点击「保存修改」写入数据库并更新 Excel；下载按钮将导出最新文件。
      </el-text>

      <TablePreviewEditor
        :table-key="tableKey"
        :preview="preview"
        :can-edit="canEdit"
        :loading="loading"
        @dirty="markDirty"
      />

      <VerificationExcerptTable
        :job-id="jobId"
        :table-key="tableKey"
        :status="status"
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
  font-size: 18px;
  font-weight: 600;
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
