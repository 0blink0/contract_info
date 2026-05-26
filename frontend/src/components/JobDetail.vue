<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { JobDetail } from '@/api/types'
import { downloadBlob, getJob, runJob } from '@/api/client'
import {
  canRetry,
  canStartRun,
  isInProgress,
  statusLabelZh,
} from '@/constants/status'
import { useJobPoll } from '@/composables/useJobPoll'
import ProcessStepper from './ProcessStepper.vue'
import WarningsList from './WarningsList.vue'
import ExportPreview from './ExportPreview.vue'

const props = defineProps<{
  jobId: string | null
}>()

const emit = defineEmits<{
  refreshList: []
  updated: []
}>()

const detail = ref<JobDetail | null>(null)
const loading = ref(false)
const running = ref(false)
const status = ref('')

const showStart = computed(
  () => detail.value && detail.value.status === 'pending',
)
const showRetry = computed(() => detail.value && canRetry(detail.value.status))
const showDownloads = computed(() => detail.value?.status === 'exported')

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
  () => props.jobId,
  (id) => {
    if (id) void loadDetail(id)
    else {
      detail.value = null
      status.value = ''
    }
  },
  { immediate: true },
)

useJobPoll(
  computed(() => props.jobId),
  status,
  (d) => {
    detail.value = d
    emit('updated')
    if (!isInProgress(d.status)) {
      emit('refreshList')
    }
  },
)

async function onStartOrRetry() {
  if (!props.jobId || !detail.value) return
  if (!canStartRun(detail.value.status) && !canRetry(detail.value.status)) return
  running.value = true
  try {
    const res = await runJob(props.jobId)
    status.value = res.status
    ElMessage.success('已开始处理')
    await loadDetail(props.jobId)
    emit('refreshList')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '启动失败')
  } finally {
    running.value = false
  }
}

async function onDownload(kind: 'product-elements' | 'fee-rates', filename: string) {
  if (!props.jobId) return
  try {
    await downloadBlob(props.jobId, kind, filename)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '下载失败')
  }
}
</script>

<template>
  <div class="job-detail">
    <el-empty v-if="!jobId" description="请选择或上传一份合同" />
    <el-skeleton v-else-if="loading && !detail" :rows="6" animated />
    <template v-else-if="detail">
      <h2 class="filename">{{ detail.filename }}</h2>
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
          <el-button type="success" @click="onDownload('product-elements', 'product_elements.xlsx')">
            下载产品要素
          </el-button>
          <el-button type="success" @click="onDownload('fee-rates', 'fee_rates.xlsx')">
            下载运营费率
          </el-button>
        </template>
      </div>

      <WarningsList
        :warnings="detail.extraction_warnings"
        :count="detail.extraction_warnings_count"
      />

      <ExportPreview :job-id="jobId" :status="detail.status" />
    </template>
  </div>
</template>

<style scoped>
.job-detail {
  padding: 8px 16px;
}
.filename {
  font-size: 18px;
  margin: 0 0 8px;
  word-break: break-all;
}
.status-line {
  margin: 0 0 12px;
  color: #606266;
}
.raw-status {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
.error-box {
  margin-bottom: 12px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
</style>
