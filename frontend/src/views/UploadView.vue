<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, View } from '@element-plus/icons-vue'
import { getJob, runJob, upload } from '@/api/client'
import type { JobDetail } from '@/api/types'
import ProcessStepper from '@/components/ProcessStepper.vue'
import { useJobPoll } from '@/composables/useJobPoll'
import {
  canRetry,
  canStartRun,
  isPipelineActive,
  statusLabelZh,
} from '@/constants/status'

const router = useRouter()

const uploading = ref(false)
const running = ref(false)
const activeJobId = ref<string | null>(null)
const detail = ref<JobDetail | null>(null)
const status = ref('')

const PREVIEW_READY = new Set([
  'extracted',
  'exporting',
  'exported',
  'export_failed',
])

const showStart = computed(
  () => detail.value && canStartRun(detail.value.status),
)
const showRetry = computed(() => detail.value && canRetry(detail.value.status))
const showViewResult = computed(
  () => detail.value && PREVIEW_READY.has(detail.value.status),
)
const busy = computed(() =>
  Boolean(detail.value && isPipelineActive(detail.value.status)),
)

async function onFileChange(file: { raw?: File }) {
  const raw = file.raw
  if (!raw) return
  if (!raw.name.toLowerCase().endsWith('.docx')) {
    ElMessage.error('仅支持 .docx 文件')
    return
  }
  uploading.value = true
  try {
    const res = await upload(raw)
    activeJobId.value = res.job_id
    detail.value = await getJob(res.job_id)
    status.value = detail.value.status
    ElMessage.success('上传成功，可开始解析')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    uploading.value = false
  }
}

async function onStartOrRetry() {
  if (!activeJobId.value || !detail.value) return
  running.value = true
  try {
    await runJob(activeJobId.value)
    detail.value = await getJob(activeJobId.value)
    status.value = detail.value.status
    poll.activate()
    ElMessage.success('已开始处理')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '启动失败')
  } finally {
    running.value = false
  }
}

function goToDetail() {
  if (!activeJobId.value) return
  void router.push({ name: 'job-hub', params: { id: activeJobId.value } })
}

const poll = useJobPoll(
  computed(() => activeJobId.value),
  status,
  (d) => {
    const prev = detail.value?.status
    detail.value = d
    if (prev && isPipelineActive(prev) && d.status === 'exported') {
      ElMessage.success('处理完成，可查看结果')
    }
  },
)
</script>

<template>
  <div class="page-shell">
    <h1 class="page-title">文件上传解析</h1>
    <p class="page-desc">上传私募基金合同 docx，自动完成解析、抽取与 Excel 导出。</p>

    <div class="surface-card upload-card">
      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="false"
        accept=".docx"
        :disabled="uploading || busy"
        class="upload-drop"
        @change="onFileChange"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽或点击上传合同
          <em>.docx</em>
        </div>
      </el-upload>
    </div>

    <div v-if="detail" class="surface-card progress-card">
      <div class="progress-header">
        <div>
          <div class="progress-label">当前文件</div>
          <div class="progress-name">{{ detail.filename }}</div>
        </div>
        <el-tag :type="busy ? 'warning' : showViewResult ? 'success' : 'info'">
          {{ statusLabelZh(detail.status) }}
        </el-tag>
      </div>

      <ProcessStepper :status="detail.status" />

      <el-alert
        v-if="detail.error_message"
        type="error"
        :title="detail.error_message"
        show-icon
        :closable="false"
        class="error-box"
      />

      <div class="progress-actions">
        <el-button
          v-if="showStart"
          type="primary"
          :loading="running"
          @click="onStartOrRetry"
        >
          开始处理
        </el-button>
        <el-button
          v-if="showRetry"
          type="warning"
          :loading="running"
          @click="onStartOrRetry"
        >
          重试
        </el-button>
        <el-button
          v-if="showViewResult"
          type="success"
          :icon="View"
          @click="goToDetail"
        >
          查看结果
        </el-button>
      </div>

      <p v-if="showViewResult" class="hint">
        解析与抽取已完成，可进入详情页查看校验、预览与下载 Excel。
      </p>
      <p v-else-if="detail.status === 'pending'" class="hint">
        上传成功，请点击「开始处理」启动解析流程。
      </p>
      <p v-else-if="busy" class="hint">正在处理中，请稍候…</p>
    </div>
  </div>
</template>

<style scoped>
.upload-card :deep(.el-upload-dragger) {
  border-radius: 10px;
  padding: 36px 20px;
  border-color: #cbd5e1;
  background: #f8fafc;
}

.upload-card :deep(.el-upload-dragger:hover) {
  border-color: var(--app-primary);
}

.upload-icon {
  font-size: 48px;
  color: var(--app-primary);
  margin-bottom: 8px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
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
  gap: 10px;
  margin-top: 16px;
}

.error-box {
  margin-top: 12px;
}

.hint {
  margin: 12px 0 0;
  font-size: 13px;
  color: #64748b;
}
</style>
