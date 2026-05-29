<script setup lang="ts">
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { JOB_FIELD_B } from '@/constants/jobSections'
import { statusLabelZh } from '@/constants/status'

const { detail } = useJobDetailInject()
</script>

<template>
  <div class="field-b-view">
    <h3 class="section-title">{{ JOB_FIELD_B.label }}</h3>
    <p v-if="detail" class="status-hint">
      任务状态：{{ statusLabelZh(detail.status) }}
    </p>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="字段 B 摘录与导出将在下一阶段开放"
      description="业绩报酬、开放日建议摘录与 path-b JSON 导出将在 Phase 18 接入。"
    />
  </div>
</template>

<style scoped>
.section-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
}

.status-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: #64748b;
}
</style>
