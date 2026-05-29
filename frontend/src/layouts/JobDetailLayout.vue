<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { DownloadKind, JobDetail } from '@/api/types'
import { deleteJob, downloadBlob, getJob, runJob } from '@/api/client'
import {
  canRetry,
  canStartRun,
  isInProgress,
  statusLabelZh,
} from '@/constants/status'
import {
  JOB_TABLE_SECTIONS,
  TABLE_DOWNLOAD_FILES,
  type TableKey,
} from '@/constants/jobSections'
import { useJobPoll } from '@/composables/useJobPoll'
import { JOB_DETAIL_KEY } from '@/composables/useJobDetailContext'
import ProcessStepper from '@/components/ProcessStepper.vue'

const route = useRoute()
const router = useRouter()

const jobId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

const isHubRoute = computed(() => route.name === 'job-hub')

const backLabel = computed(() =>
  isHubRoute.value ? '← 返回文件列表' : '← 返回文件详情',
)

function onBack() {
  if (isHubRoute.value) {
    void router.push({ name: 'jobs' })
    return
  }
  if (jobId.value) {
    void router.push({ name: 'job-hub', params: { id: jobId.value } })
  }
}

const detail = ref<JobDetail | null>(null)
const loading = ref(false)
const running = ref(false)
const status = ref('')
const downloadingReport = ref(false)

const PREVIEW_PLUS = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

const showStart = computed(() => detail.value?.status === 'pending')
const showRetry = computed(() => detail.value && canRetry(detail.value.status))
const showDownloads = computed(() => detail.value?.status === 'exported')
const showReportDownload = computed(
  () => Boolean(detail.value && PREVIEW_PLUS.has(detail.value.status)),
)
const canDelete = computed(
  () => detail.value && !isInProgress(detail.value.status),
)

async function loadDetail(id: string) {
  loading.value = true
  try {
    detail.value = await getJob(id)
    status.value = detail.value.status
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(
  jobId,
  (id) => {
    if (id) void loadDetail(id)
    else {
      detail.value = null
      status.value = ''
    }
  },
  { immediate: true },
)

const poll = useJobPoll(jobId, status, (d) => {
  detail.value = d
})

provide(JOB_DETAIL_KEY, {
  jobId,
  detail,
  loading,
  status,
  refresh: poll.refresh,
  activate: poll.activate,
})

async function onStartOrRetry() {
  if (!jobId.value || !detail.value) return
  if (!canStartRun(detail.value.status) && !canRetry(detail.value.status)) return
  running.value = true
  try {
    await runJob(jobId.value)
    ElMessage.success('已开始处理')
    await loadDetail(jobId.value)
    poll.activate()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '启动失败')
  } finally {
    running.value = false
  }
}

async function onDelete() {
  if (!jobId.value || !detail.value) return
  try {
    await ElMessageBox.confirm(
      `确定删除「${detail.value.filename}」？将同时删除上传文件、导出 Excel 及数据库记录，且不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteJob(jobId.value)
    ElMessage.success('已删除')
    void router.push({ name: 'jobs' })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

async function onDownload(kind: DownloadKind, filename: string) {
  if (!jobId.value) return
  try {
    await downloadBlob(jobId.value, kind, filename)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '下载失败')
  }
}

function downloadTable(key: TableKey) {
  void onDownload(key as DownloadKind, TABLE_DOWNLOAD_FILES[key])
}

async function onDownloadReport() {
  if (!jobId.value) return
  downloadingReport.value = true
  try {
    await downloadBlob(jobId.value, 'review-report', '核对报告.xlsx')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '下载失败')
  } finally {
    downloadingReport.value = false
  }
}
</script>

<template>
  <div class="page-shell detail-layout">
    <el-button class="back-btn" text @click="onBack">
      {{ backLabel }}
    </el-button>

    <el-empty v-if="!jobId" description="无效的任务链接" />

    <el-skeleton v-else-if="loading && !detail" :rows="6" animated />

    <template v-else-if="detail">
      <div class="title-row">
        <h2 class="filename">{{ detail.filename }}</h2>
        <el-button
          v-if="canDelete"
          type="danger"
          plain
          size="small"
          @click="onDelete"
        >
          删除
        </el-button>
      </div>

      <p class="status-line">
        状态：<el-tag>{{ statusLabelZh(detail.status) }}</el-tag>
        <span class="raw-status">{{ detail.status }}</span>
      </p>

      <ProcessStepper :status="detail.status" />

      <el-alert
        v-if="detail.error_message"
        type="error"
        :title="detail.error_message"
        show-icon
        :closable="false"
        class="error-box"
      />

      <div class="actions">
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
        <template v-if="showDownloads">
          <el-button
            v-for="sec in JOB_TABLE_SECTIONS"
            :key="sec.key"
            type="success"
            @click="downloadTable(sec.key)"
          >
            下载{{ sec.label }}
          </el-button>
        </template>
        <el-button
          v-if="showReportDownload"
          type="primary"
          :loading="downloadingReport"
          @click="onDownloadReport"
        >
          下载核对报告
        </el-button>
      </div>

      <div class="child-shell surface-card">
        <router-view />
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-layout {
  padding-top: 16px;
}

.back-btn {
  margin-bottom: 8px;
  color: #64748b;
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--app-border);
}

.filename {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  word-break: break-all;
  flex: 1;
  color: #0f172a;
}

.status-line {
  margin: 0 0 16px;
  color: #64748b;
}

.raw-status {
  margin-left: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.error-box {
  margin-bottom: 12px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid var(--app-border);
}

.child-shell {
  margin-top: 8px;
  padding: 20px;
}
</style>
