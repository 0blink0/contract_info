<script setup lang="ts">

import { computed, ref, watch } from 'vue'

import { ElMessage, ElMessageBox } from 'element-plus'

import type { DownloadKind, JobDetail } from '@/api/types'

import { deleteJob, downloadBlob, getJob, runJob } from '@/api/client'

import {

  canRetry,

  canStartRun,

  isInProgress,

  statusLabelZh,

} from '@/constants/status'

import { useJobPoll } from '@/composables/useJobPoll'

import ProcessStepper from './ProcessStepper.vue'

import WarningsList from './WarningsList.vue'

import ValidationPanel from './ValidationPanel.vue'

import PathBPanel from './PathBPanel.vue'

import ExportPreview from './ExportPreview.vue'



const props = defineProps<{

  jobId: string | null

}>()



const emit = defineEmits<{

  refreshList: []

  updated: []

  deleted: [jobId: string]

}>()



const detail = ref<JobDetail | null>(null)

const loading = ref(false)

const running = ref(false)

const status = ref('')



const PREVIEW_PLUS = new Set(['extracted', 'exporting', 'exported', 'export_failed'])



const showStart = computed(

  () => detail.value && detail.value.status === 'pending',

)

const showRetry = computed(() => detail.value && canRetry(detail.value.status))

const showDownloads = computed(() => detail.value?.status === 'exported')

const showPanels = computed(

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



async function onDelete() {

  if (!props.jobId || !detail.value) return

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

    await deleteJob(props.jobId)

    ElMessage.success('已删除')

    emit('deleted', props.jobId)

    emit('refreshList')

  } catch (e) {

    ElMessage.error(e instanceof Error ? e.message : '删除失败')

  }

}



async function onDownload(kind: DownloadKind, filename: string) {

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

          <el-button type="success" @click="onDownload('product-elements', 'product_elements.xlsx')">

            下载产品要素

          </el-button>

          <el-button type="success" @click="onDownload('fee-rates', 'fee_rates.xlsx')">

            下载运营费率

          </el-button>

          <el-button type="success" @click="onDownload('lock-periods', 'lock_periods.xlsx')">

            下载份额锁定期

          </el-button>

          <el-button type="success" @click="onDownload('share-classes', 'share_classes.xlsx')">

            下载分级份额

          </el-button>

          <el-button

            type="success"

            @click="onDownload('subscription-fee-rates', 'subscription_fee_rates.xlsx')"

          >

            下载申赎费率

          </el-button>

        </template>

      </div>



      <WarningsList

        :warnings="detail.extraction_warnings"

        :count="detail.extraction_warnings_count"

      />



      <ValidationPanel

        :job-id="jobId"

        :visible="showPanels"

        :available="detail.validation_available"

        :fail-count="detail.validation_fail_count"

        :warn-count="detail.validation_warn_count"

      />



      <PathBPanel

        :job-id="jobId"

        :visible="showPanels"

        :available="detail.path_b_available"

      />



      <ExportPreview :job-id="jobId" :status="detail.status" />

    </template>

  </div>

</template>



<style scoped>

.job-detail {

  padding: 8px 16px;

}

.title-row {

  display: flex;

  align-items: flex-start;

  justify-content: space-between;

  gap: 12px;

  margin-bottom: 8px;

}

.filename {

  font-size: 18px;

  margin: 0;

  word-break: break-all;

  flex: 1;

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

