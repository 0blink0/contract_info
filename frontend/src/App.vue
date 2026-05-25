<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listJobs } from '@/api/client'
import type { JobListItem } from '@/api/types'
import JobList from '@/components/JobList.vue'
import JobDetail from '@/components/JobDetail.vue'
import UploadPanel from '@/components/UploadPanel.vue'

const items = ref<JobListItem[]>([])
const listLoading = ref(false)
const selectedId = ref<string | null>(null)

async function refreshList() {
  listLoading.value = true
  try {
    const res = await listJobs(20)
    items.value = res.items
  } finally {
    listLoading.value = false
  }
}

function onUploaded(jobId: string) {
  selectedId.value = jobId
  void refreshList()
}

function onSelect(jobId: string) {
  selectedId.value = jobId
}

onMounted(() => {
  void refreshList()
})
</script>

<template>
  <el-container class="layout">
    <el-header class="header">
      <h1>合同要素抽取</h1>
      <span class="subtitle">上传 docx → 生成可导入 Excel</span>
    </el-header>
    <el-container>
      <el-aside width="320px" class="aside">
        <JobList
          :items="items"
          :selected-id="selectedId"
          :loading="listLoading"
          @select="onSelect"
        />
        <UploadPanel @uploaded="onUploaded" />
      </el-aside>
      <el-main class="main">
        <JobDetail
          :job-id="selectedId"
          @refresh-list="refreshList"
          @updated="refreshList"
        />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: baseline;
  gap: 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}
.header h1 {
  margin: 0;
  font-size: 20px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
}
.aside {
  background: #fafafa;
  border-right: 1px solid #ebeef5;
  padding: 16px;
}
.main {
  background: #fff;
}
</style>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
</style>
