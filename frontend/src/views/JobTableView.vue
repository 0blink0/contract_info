<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { isValidTableKey, sectionLabel } from '@/constants/jobSections'
import { statusLabelZh } from '@/constants/status'

const route = useRoute()
const { detail } = useJobDetailInject()

const tableKey = computed(() => {
  const k = route.params.tableKey
  return typeof k === 'string' ? k : ''
})

const label = computed(() => {
  if (isValidTableKey(tableKey.value)) return sectionLabel(tableKey.value)
  return tableKey.value
})
</script>

<template>
  <div class="table-view">
    <h3 class="section-title">{{ label }}</h3>
    <p v-if="detail" class="status-hint">
      任务状态：{{ statusLabelZh(detail.status) }}
    </p>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="本页编辑与摘录核对功能将在下一阶段开放"
      description="当前为导航骨架；保存、核对表与单表下载将在 Phase 17 接入。"
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
