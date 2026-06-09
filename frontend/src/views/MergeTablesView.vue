<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Delete, View, Tickets } from '@element-plus/icons-vue'
import { listJobs } from '@/api/client'
import {
  appendToMerge,
  createMerge,
  deleteAllMergeRecords,
  deleteMergeRecord,
  downloadMergeBlob,
  getMergePreview,
  listMerges,
} from '@/api/client'
import type { JobListItem, MergePreview, MergeRecord } from '@/api/types'
import { JOB_TABLE_SECTIONS } from '@/constants/jobSections'

// ── file list ──────────────────────────────────────────────────
const exportedJobs = ref<JobListItem[]>([])
const jobsLoading = ref(false)
const selectedJobIds = ref<string[]>([])

async function loadJobs() {
  jobsLoading.value = true
  try {
    const res = await listJobs(200)
    exportedJobs.value = (res.items ?? []).filter((j) => j.status === 'exported')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载文件列表失败')
  } finally {
    jobsLoading.value = false
  }
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

// ── table type multi-select ────────────────────────────────────
const selectedTableTypes = ref<string[]>([])

const tableTypeOptions = JOB_TABLE_SECTIONS.map((s) => ({
  value: s.key,
  label: s.label,
}))

// ── merge action ───────────────────────────────────────────────
const merging = ref(false)
// one result card per table type (keyed by table_type)
const latestResults = ref<MergeRecord[]>([])

// per-type progress state while merging
const mergingTypes = ref<Set<string>>(new Set())

async function onMerge() {
  if (selectedJobIds.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return
  }
  if (selectedTableTypes.value.length === 0) {
    ElMessage.warning('请至少选择一种表格类型')
    return
  }

  merging.value = true
  mergingTypes.value = new Set(selectedTableTypes.value)
  latestResults.value = []

  // fire all selected types in parallel
  const tasks = selectedTableTypes.value.map((type) =>
    createMerge(selectedJobIds.value, type).then(
      (record) => {
        mergingTypes.value.delete(type)
        return { ok: true as const, record }
      },
      (err) => {
        mergingTypes.value.delete(type)
        const label = tableTypeOptions.find((o) => o.value === type)?.label ?? type
        ElMessage.error(`${label} 合并失败：${err instanceof Error ? err.message : '未知错误'}`)
        return { ok: false as const, type }
      },
    ),
  )

  const results = await Promise.all(tasks)
  latestResults.value = results.filter((r) => r.ok).map((r) => (r as { ok: true; record: MergeRecord }).record)

  const successCount = latestResults.value.length
  if (successCount > 0) {
    ElMessage.success(
      successCount === selectedTableTypes.value.length
        ? `全部 ${successCount} 种表格合并完成`
        : `${successCount} 种表格合并完成，${selectedTableTypes.value.length - successCount} 种失败`,
    )
    await loadMerges()
  }

  merging.value = false
}

function downloadResult(record: MergeRecord) {
  void downloadMergeBlob(record.id, `${record.table_type_label}_合并.xlsx`)
}

// ── merge history ──────────────────────────────────────────────
const mergeRecords = ref<MergeRecord[]>([])
const historyLoading = ref(false)
const historyCollapsed = ref(false)

async function loadMerges() {
  historyLoading.value = true
  try {
    mergeRecords.value = await listMerges()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载合并历史失败')
  } finally {
    historyLoading.value = false
  }
}

async function onDelete(record: MergeRecord) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${record.name}」？此操作不可撤销。`,
      '删除合并表格',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteMergeRecord(record.id)
    ElMessage.success('已删除')
    latestResults.value = latestResults.value.filter((r) => r.id !== record.id)
    await loadMerges()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

function onDownload(record: MergeRecord) {
  void downloadMergeBlob(record.id, `${record.table_type_label}_合并.xlsx`)
}

async function onDeleteAll() {
  try {
    await ElMessageBox.confirm(
      `确认删除全部 ${mergeRecords.value.length} 条合并记录及对应文件？此操作不可撤销。`,
      '清空合并记录',
      { type: 'warning', confirmButtonText: '全部删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const count = await deleteAllMergeRecords()
    ElMessage.success(`已删除 ${count} 条记录`)
    latestResults.value = []
    await loadMerges()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

// ── append dialog ──────────────────────────────────────────────
const appendVisible = ref(false)
const appendTarget = ref<MergeRecord | null>(null)
const appendSelectedIds = ref<string[]>([])
const appending = ref(false)

const appendCandidates = computed<JobListItem[]>(() => {
  if (!appendTarget.value) return []
  const existingIds = new Set(appendTarget.value.source_jobs.map((s) => s.job_id))
  return exportedJobs.value.filter((j) => !existingIds.has(j.job_id))
})

function onAppend(record: MergeRecord) {
  appendTarget.value = record
  appendSelectedIds.value = []
  appendVisible.value = true
}

async function confirmAppend() {
  if (!appendTarget.value || appendSelectedIds.value.length === 0) return
  appending.value = true
  try {
    const updated = await appendToMerge(appendTarget.value.id, appendSelectedIds.value)
    ElMessage.success(`已追加 ${appendSelectedIds.value.length} 个文件，当前共 ${updated.row_count} 行`)
    appendVisible.value = false
    await loadMerges()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '追加失败')
  } finally {
    appending.value = false
  }
}

// ── preview dialog ─────────────────────────────────────────────
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref<MergePreview | null>(null)
const previewTitle = ref('')

async function onPreview(record: MergeRecord) {
  previewTitle.value = record.name
  previewVisible.value = true
  previewLoading.value = true
  previewData.value = null
  try {
    previewData.value = await getMergePreview(record.id)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载预览失败')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

const previewColumns = computed(() => previewData.value?.columns ?? [])
const previewRows = computed(() => previewData.value?.rows ?? [])

onMounted(() => {
  void loadJobs()
  void loadMerges()
})
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <h1 class="page-title">表格合并</h1>
      <p class="page-desc">选择已导出的合同文件，勾选需要合并的表格类型，每种类型独立生成一个合并文件。</p>
    </div>

    <!-- ── Step 1: select files ── -->
    <div class="surface-card section-card">
      <div class="section-title">第一步：选择文件</div>
      <p class="section-hint">仅显示已完成导出（状态为「已导出」）的合同文件。</p>
      <el-table
        v-loading="jobsLoading"
        :data="exportedJobs"
        stripe
        style="width: 100%"
        max-height="320"
        empty-text="暂无已导出的文件"
        @selection-change="(rows: JobListItem[]) => (selectedJobIds = rows.map((r) => r.job_id))"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="filename" label="文件名" min-width="300" show-overflow-tooltip />
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
      <div v-if="selectedJobIds.length > 0" class="selected-hint">
        已选择 {{ selectedJobIds.length }} 个文件
      </div>
    </div>

    <!-- ── Step 2: select table types (multi) + merge ── -->
    <div class="surface-card section-card">
      <div class="section-title">第二步：选择表格类型（可多选，每种独立合并）</div>
      <div class="step2-body">
        <div class="type-checkbox-group">
          <el-checkbox
            v-for="opt in tableTypeOptions"
            :key="opt.value"
            v-model="selectedTableTypes"
            :label="opt.value"
            border
            class="type-checkbox"
          >
            {{ opt.label }}
          </el-checkbox>
        </div>
        <div class="step2-actions">
          <el-button
            link
            size="small"
            :disabled="selectedTableTypes.length === tableTypeOptions.length"
            @click="selectedTableTypes = tableTypeOptions.map((o) => o.value)"
          >
            全选
          </el-button>
          <el-button
            link
            size="small"
            :disabled="selectedTableTypes.length === 0"
            @click="selectedTableTypes = []"
          >
            清空
          </el-button>
          <el-button
            type="primary"
            :loading="merging"
            :disabled="selectedJobIds.length === 0 || selectedTableTypes.length === 0"
            @click="onMerge"
          >
            <el-icon><Tickets /></el-icon>
            开始合并
            <span v-if="selectedTableTypes.length > 0" class="merge-count-hint">
              （{{ selectedTableTypes.length }} 种）
            </span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- ── Merge results: one card per type ── -->
    <template v-if="latestResults.length > 0 || mergingTypes.size > 0">
      <div class="results-grid">
        <!-- in-progress placeholders -->
        <div
          v-for="type in [...mergingTypes]"
          :key="'pending-' + type"
          class="surface-card result-card result-card--loading"
        >
          <div class="result-header">
            <el-tag size="small" type="info">
              {{ tableTypeOptions.find((o) => o.value === type)?.label ?? type }}
            </el-tag>
          </div>
          <el-skeleton :rows="2" animated style="margin-top: 8px" />
        </div>
        <!-- completed result cards -->
        <div
          v-for="record in latestResults"
          :key="record.id"
          class="surface-card result-card result-card--done"
        >
          <div class="result-header">
            <div>
              <el-tag type="success" size="small">{{ record.table_type_label }}</el-tag>
            </div>
            <el-button size="small" type="primary" @click="downloadResult(record)">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
          </div>
          <div class="result-meta">
            {{ record.source_jobs.length }} 个文件 · {{ record.row_count }} 行数据
          </div>
        </div>
      </div>
    </template>

    <!-- ── History management ── -->
    <div class="surface-card section-card history-card">
      <div class="history-header" @click="historyCollapsed = !historyCollapsed">
        <div class="section-title" style="margin-bottom: 0">
          已合并表格管理
        </div>
        <div class="history-header-right" @click.stop>
          <el-button
            v-if="mergeRecords.length > 0"
            type="danger"
            size="small"
            plain
            @click="onDeleteAll"
          >
            <el-icon><Delete /></el-icon>
            清空全部
          </el-button>
          <el-icon class="collapse-icon" :class="{ collapsed: historyCollapsed }" @click="historyCollapsed = !historyCollapsed">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path d="M7 10l5 5 5-5z" fill="currentColor" />
            </svg>
          </el-icon>
        </div>
      </div>

      <template v-if="!historyCollapsed">
        <el-table
          v-loading="historyLoading"
          :data="mergeRecords"
          stripe
          style="width: 100%; margin-top: 12px"
          empty-text="暂无合并记录"
        >
          <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.table_type_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="来源文件" min-width="220">
            <template #default="{ row }">
              <span class="source-files-text">
                {{ row.source_jobs.map((s: any) => s.filename).join('、') }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="行数" width="72" align="right">
            <template #default="{ row }">{{ row.row_count }}</template>
          </el-table-column>
          <el-table-column label="合并时间" width="175">
            <template #default="{ row }">{{ formatTime(row.merged_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="onPreview(row)">
                <el-icon><View /></el-icon>预览
              </el-button>
              <el-button type="warning" link @click="onAppend(row)">
                追加
              </el-button>
              <el-button type="success" link @click="onDownload(row)">
                <el-icon><Download /></el-icon>下载
              </el-button>
              <el-button type="danger" link @click="onDelete(row)">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </div>

    <!-- ── Append dialog ── -->
    <el-dialog
      v-model="appendVisible"
      :title="`追加文件到「${appendTarget?.name ?? ''}」`"
      width="680px"
      destroy-on-close
    >
      <div v-if="appendCandidates.length === 0" style="color: var(--el-text-color-secondary); padding: 12px 0;">
        没有可追加的文件（已选文件均已包含在本合并中，或暂无其他已导出文件）。
      </div>
      <template v-else>
        <p style="font-size: 13px; color: var(--el-text-color-secondary); margin: 0 0 10px;">
          选择要追加进合并表的已导出文件（不含已包含的来源）：
        </p>
        <el-table
          :data="appendCandidates"
          stripe
          max-height="320"
          style="width: 100%"
          @selection-change="(rows: JobListItem[]) => (appendSelectedIds = rows.map((r) => r.job_id))"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="filename" label="文件名" min-width="300" show-overflow-tooltip />
          <el-table-column label="上传时间" width="175">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
        <div v-if="appendSelectedIds.length > 0" style="margin-top: 8px; font-size: 13px; color: var(--el-color-primary);">
          已选 {{ appendSelectedIds.length }} 个文件
        </div>
      </template>
      <template #footer>
        <el-button @click="appendVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="appending"
          :disabled="appendSelectedIds.length === 0"
          @click="confirmAppend"
        >
          确认追加
        </el-button>
      </template>
    </el-dialog>

    <!-- ── Preview dialog ── -->
    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="85%"
      top="5vh"
      destroy-on-close
    >
      <el-skeleton v-if="previewLoading" :rows="5" animated />
      <template v-else-if="previewData">
        <div class="preview-meta">共 {{ previewRows.length }} 行（最多展示 100 行）</div>
        <el-table
          :data="previewRows"
          stripe
          border
          size="small"
          max-height="520"
          style="width: 100%"
          empty-text="无数据"
        >
          <el-table-column
            v-for="col in previewColumns"
            :key="col"
            :label="col"
            :prop="col"
            min-width="120"
            show-overflow-tooltip
          />
        </el-table>
      </template>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 4px;
}

.section-card {
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
}

.section-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0 0 10px;
}

.selected-hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-color-primary);
}

/* step 2 */
.step2-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.type-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.type-checkbox {
  margin-right: 0 !important;
}

.step2-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.merge-count-hint {
  margin-left: 2px;
  font-size: 12px;
  opacity: 0.85;
}

/* result cards grid */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
  align-items: stretch;
}

.result-card {
  padding: 14px 16px;
  min-height: 88px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  margin-top: 0 !important;
}

.result-card--loading {
  opacity: 0.7;
}

.result-card--done {
  border-left: 3px solid var(--el-color-success);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.result-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: auto;
}

/* history */
.history-card {
  padding-bottom: 12px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}

.history-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-icon {
  transition: transform 0.2s ease;
  color: var(--el-text-color-secondary);
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.source-files-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.preview-meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}
</style>
