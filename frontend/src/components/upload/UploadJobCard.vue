<script setup lang="ts">
import { computed } from 'vue'
import { View } from '@element-plus/icons-vue'
import ProcessStepper from '@/components/ProcessStepper.vue'
import type { UploadSessionJob } from '@/constants/upload'
import {
  canRetry,
  canStartRun,
  isPipelineActive,
  statusLabelZh,
} from '@/constants/status'

const props = defineProps<{
  job: UploadSessionJob
  running?: boolean
}>()

const emit = defineEmits<{
  start: []
  'view-result': []
}>()

const PREVIEW_READY = new Set([
  'extracted',
  'exporting',
  'exported',
  'export_failed',
])

const busy = computed(() => isPipelineActive(props.job.status))
const showStart = computed(() => canStartRun(props.job.status))
const showRetry = computed(() => canRetry(props.job.status))
const showViewResult = computed(() => PREVIEW_READY.has(props.job.status))
</script>

<template>
  <div class="upload-job-card surface-card">
    <div class="progress-header">
      <div>
        <div class="progress-label">文件</div>
        <div class="progress-name">{{ job.filename }}</div>
      </div>
      <el-tag :type="busy ? 'warning' : showViewResult ? 'success' : 'info'">
        {{ statusLabelZh(job.status) }}
      </el-tag>
    </div>

    <ProcessStepper :status="job.status" />

    <el-alert
      v-if="job.detail.error_message"
      type="error"
      :title="job.detail.error_message"
      show-icon
      :closable="false"
      class="error-box"
    />

    <div class="progress-actions">
      <el-button
        v-if="showStart"
        type="primary"
        size="small"
        :loading="running"
        @click="emit('start')"
      >
        开始处理
      </el-button>
      <el-button
        v-if="showRetry"
        type="warning"
        size="small"
        :loading="running"
        @click="emit('start')"
      >
        重试
      </el-button>
      <el-button
        v-if="showViewResult"
        type="success"
        size="small"
        :icon="View"
        @click="emit('view-result')"
      >
        查看结果
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.upload-job-card {
  margin-bottom: 16px;
  padding: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.progress-label {
  font-size: 12px;
  color: #64748b;
}

.progress-name {
  font-size: 15px;
  font-weight: 600;
  margin-top: 4px;
  word-break: break-all;
}

.progress-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.error-box {
  margin-top: 8px;
}
</style>
