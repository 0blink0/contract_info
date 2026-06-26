<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import UploadJobCard from '@/components/upload/UploadJobCard.vue'
import { createJobsPoll } from '@/composables/useJobsPoll'
import {
  getJob,
  getJobConcurrency,
  parseApiError,
  runJob,
  upload,
} from '@/api/client'
import type { JobConcurrencyResponse, JobDetail } from '@/api/types'
import {
  MAX_PARALLEL_JOBS,
  MAX_UPLOAD_FILES,
  type UploadSessionJob,
} from '@/constants/upload'
import { isPipelineActive } from '@/constants/status'

const router = useRouter()
const jobsPoll = createJobsPoll()

const sessionJobs = ref<UploadSessionJob[]>([])
const processedUids = ref(new Set<string>())
const uploading = ref(false)
const runningJobId = ref<string | null>(null)
const batchRunning = ref(false)
const concurrency = ref<JobConcurrencyResponse>({
  active: 0,
  queued: 0,
  max: MAX_PARALLEL_JOBS,
})

let concurrencyTimer: ReturnType<typeof setInterval> | null = null

const pendingJobs = computed(() =>
  sessionJobs.value.filter((j) => j.status === 'pending'),
)

const canBatchStart = computed(
  () => pendingJobs.value.length > 0 && !batchRunning.value && !uploading.value,
)

const uploadDisabled = computed(
  () => uploading.value || sessionJobs.value.length >= MAX_UPLOAD_FILES,
)

const anyBusy = computed(() =>
  sessionJobs.value.some((j) => isPipelineActive(j.status)),
)

async function refreshConcurrency() {
  try {
    concurrency.value = await getJobConcurrency()
  } catch {
    /* ignore */
  }
}

function syncJobFromPoll(jobId: string, detail: JobDetail) {
  const idx = sessionJobs.value.findIndex((j) => j.jobId === jobId)
  if (idx < 0) return
  const prev = sessionJobs.value[idx].status
  sessionJobs.value[idx] = {
    ...sessionJobs.value[idx],
    detail,
    status: detail.status,
    filename: detail.filename,
  }
  if (prev && isPipelineActive(prev) && detail.status === 'exported') {
    ElMessage.success(`${detail.filename} 处理完成`)
  }
}

async function uploadOne(file: File, uid: string | number) {
  const uidKey = String(uid)
  if (processedUids.value.has(uidKey)) return
  if (sessionJobs.value.length >= MAX_UPLOAD_FILES) {
    ElMessage.warning(`最多同时上传 ${MAX_UPLOAD_FILES} 个文件`)
    return
  }
  processedUids.value.add(uidKey)
  uploading.value = true
  try {
    const res = await upload(file)
    const detail = await getJob(res.job_id)
    const entry: UploadSessionJob = {
      jobId: res.job_id,
      filename: detail.filename,
      status: detail.status,
      detail,
    }
    sessionJobs.value.push(entry)
    jobsPoll.register(res.job_id, detail.status, (d) => syncJobFromPoll(res.job_id, d))
    ElMessage.success(`已上传：${detail.filename}`)
  } catch (e) {
    ElMessage.error(parseApiError(e))
    processedUids.value.delete(uidKey)
  } finally {
    uploading.value = false
  }
}

async function onFileChange(uploadFile: UploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  const name = raw.name.toLowerCase()
  if (!name.endsWith('.docx') && !name.endsWith('.pdf')) {
    ElMessage.error('仅支持 .docx / .pdf 文件')
    return
  }
  await uploadOne(raw, uploadFile.uid)
}

function onExceed() {
  ElMessage.warning(`最多同时上传 ${MAX_UPLOAD_FILES} 个文件`)
}

async function runOne(jobId: string) {
  runningJobId.value = jobId
  try {
    await runJob(jobId)
    const detail = await getJob(jobId)
    syncJobFromPoll(jobId, detail)
    jobsPoll.activate(jobId)
    ElMessage.success('已开始处理')
    await refreshConcurrency()
  } catch (e) {
    ElMessage.error(parseApiError(e))
  } finally {
    runningJobId.value = null
  }
}

async function batchStart() {
  if (!canBatchStart.value) return
  batchRunning.value = true
  let submitted = 0
  for (const job of [...pendingJobs.value]) {
    try {
      await runJob(job.jobId)
      const detail = await getJob(job.jobId)
      syncJobFromPoll(job.jobId, detail)
      jobsPoll.activate(job.jobId)
      submitted += 1
    } catch (e) {
      ElMessage.error(`${job.filename}：${parseApiError(e)}`)
    }
  }
  if (submitted > 0) {
    await refreshConcurrency()
    ElMessage.success(`已提交 ${submitted} 个任务`)
  }
  batchRunning.value = false
}

function goToDetail(jobId: string) {
  void router.push({ name: 'job-hub', params: { id: jobId } })
}

function clearSession() {
  for (const job of sessionJobs.value) {
    jobsPoll.unregister(job.jobId)
  }
  sessionJobs.value = []
  processedUids.value.clear()
}

onMounted(() => {
  void refreshConcurrency()
  concurrencyTimer = setInterval(() => void refreshConcurrency(), 5000)
})

onUnmounted(() => {
  if (concurrencyTimer) clearInterval(concurrencyTimer)
  jobsPoll.stop()
  for (const job of sessionJobs.value) {
    jobsPoll.unregister(job.jobId)
  }
})
</script>

<template>
  <div class="page-shell">
    <h1 class="page-title">文件上传解析</h1>
    <p class="page-desc">
      一次最多上传 {{ MAX_UPLOAD_FILES }} 份合同，系统同时处理 {{ MAX_PARALLEL_JOBS }} 个任务，其余自动排队依次跟上。
    </p>

    <el-alert
      v-if="concurrency.active > 0 || concurrency.queued > 0"
      type="info"
      :closable="false"
      show-icon
      class="concurrency-banner"
      :title="`处理中 ${concurrency.active} / ${concurrency.max}${concurrency.queued ? `，排队等待 ${concurrency.queued} 个` : ''}`"
    />

    <div class="toolbar">
      <el-button
        type="primary"
        :disabled="!canBatchStart"
        :loading="batchRunning"
        @click="batchStart"
      >
        全部开始处理
        <span v-if="pendingJobs.length">（{{ pendingJobs.length }}）</span>
      </el-button>
      <el-button
        v-if="sessionJobs.length"
        :disabled="anyBusy || uploading"
        @click="clearSession"
      >
        清空列表
      </el-button>
    </div>

    <div class="surface-card upload-card">
      <el-upload
        drag
        multiple
        :limit="MAX_UPLOAD_FILES"
        :auto-upload="false"
        :show-file-list="true"
        accept=".docx,.pdf"
        :disabled="uploadDisabled"
        class="upload-drop"
        @change="onFileChange"
        @exceed="onExceed"
      >
        <svg class="upload-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="4" y="4" width="40" height="40" rx="14" fill="currentColor" fill-opacity="0.08"/>
          <path d="M24 31L24 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
          <path d="M17 25L24 18L31 25" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="17" cy="36" r="2.2" fill="currentColor" fill-opacity="0.35"/>
          <circle cx="24" cy="36" r="2.2" fill="currentColor" fill-opacity="0.35"/>
          <circle cx="31" cy="36" r="2.2" fill="currentColor" fill-opacity="0.35"/>
        </svg>
        <div class="el-upload__text">
          拖拽或点击上传合同（最多 {{ MAX_UPLOAD_FILES }} 个）
          <em>.docx / .pdf</em>
        </div>
      </el-upload>
    </div>

    <UploadJobCard
      v-for="job in sessionJobs"
      :key="job.jobId"
      :job="job"
      :running="runningJobId === job.jobId"
      @start="runOne(job.jobId)"
      @view-result="goToDetail(job.jobId)"
    />

    <p v-if="!sessionJobs.length" class="empty-hint">
      上传后每张合同将显示独立进度卡片；处理完成后可进入详情查看与下载。
    </p>
  </div>
</template>

<style scoped>
.concurrency-banner {
  margin-bottom: 12px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

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
  width: 52px;
  height: 52px;
  color: var(--app-primary);
  margin-bottom: 10px;
}

.empty-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #64748b;
}
</style>
