<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { deleteJob, listJobs } from '@/api/client'
import type { JobListItem } from '@/api/types'
import { confirmAndDeleteJob } from '@/composables/useConfirmDeleteJob'
import { isInProgress, statusLabelZh } from '@/constants/status'

const router = useRouter()
const items = ref<JobListItem[]>([])
const loading = ref(false)
const deleting = ref(false)
const searchKeyword = ref('')

const filteredItems = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return items.value
  return items.value.filter((item) => item.filename?.toLowerCase().includes(kw))
})

const deletableItems = computed(() => items.value.filter((item) => !isInProgress(item.status)))

async function refresh() {
  loading.value = true
  try {
    const res = await listJobs(100)
    items.value = res.items ?? []
  } catch (e) {
    items.value = []
    ElMessage.error(e instanceof Error ? e.message : '加载文件列表失败')
  } finally {
    loading.value = false
  }
}

function openDetail(jobId: string) {
  void router.push({ name: 'job-hub', params: { id: jobId } })
}

async function onDelete(row: JobListItem) {
  const ok = await confirmAndDeleteJob(row.job_id, row.filename)
  if (ok) await refresh()
}

async function deleteAll() {
  const count = deletableItems.value.length
  if (count === 0) {
    ElMessage.info('没有可删除的文件（处理中的文件不可删除）')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将删除全部 ${count} 个文件及其解析记录，操作不可撤销，确认继续？`,
      '一键删除全部',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deleting.value = true
  let failed = 0
  for (const item of deletableItems.value) {
    try {
      await deleteJob(item.job_id)
    } catch {
      failed++
    }
  }
  deleting.value = false
  searchKeyword.value = ''
  await refresh()
  if (failed > 0) {
    ElMessage.warning(`${failed} 个文件删除失败，其余已清除`)
  } else {
    ElMessage.success('已删除全部文件及记录')
  }
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function statusTagType(status: string) {
  if (status === 'exported') return 'success'
  if (isInProgress(status)) return 'warning'
  if (status.includes('failed')) return 'danger'
  return 'info'
}

onMounted(() => {
  void refresh()
})

onActivated(() => {
  void refresh()
})
</script>

<template>
  <div class="page-shell">
    <div class="list-header">
      <div>
        <h1 class="page-title">文件列表</h1>
        <p class="page-desc">历史解析任务，点击进入详情查看抽取结果与下载导出文件。</p>
      </div>
      <div class="header-actions">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索文件名…"
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          type="danger"
          plain
          :disabled="deletableItems.length === 0 || deleting"
          :loading="deleting"
          @click="deleteAll"
        >
          一键删除全部
        </el-button>
        <el-button :loading="loading" @click="refresh">刷新</el-button>
      </div>
    </div>

    <div class="surface-card">
      <el-table
        v-loading="loading"
        :data="filteredItems"
        stripe
        style="width: 100%"
        empty-text="暂无文件，请先在「文件上传解析」页上传合同"
        @row-click="(row: JobListItem) => openDetail(row.job_id)"
      >
        <el-table-column prop="filename" label="文件名" min-width="280" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)">
              {{ statusLabelZh(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="openDetail(row.job_id)">
              查看详情
            </el-button>
            <el-button
              type="danger"
              link
              :disabled="isInProgress(row.status)"
              @click.stop="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 4px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.search-input {
  width: 220px;
}

:deep(.el-table__row) {
  cursor: pointer;
}
</style>
