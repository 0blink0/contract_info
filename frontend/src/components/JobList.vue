<script setup lang="ts">
import type { JobListItem } from '@/api/types'
import { statusLabelZh } from '@/constants/status'

defineProps<{
  items: JobListItem[]
  selectedId: string | null
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [jobId: string]
}>()

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}
</script>

<template>
  <div class="job-list">
    <div class="job-list-title">近期任务</div>
    <el-skeleton v-if="loading" :rows="4" animated />
    <el-empty v-else-if="items.length === 0" description="暂无任务" />
    <ul v-else class="job-list-items">
      <li
        v-for="item in items"
        :key="item.job_id"
        :class="{ active: item.job_id === selectedId }"
        @click="emit('select', item.job_id)"
      >
        <div class="name" :title="item.filename">{{ item.filename }}</div>
        <div class="meta">
          <el-tag size="small" type="info">{{ statusLabelZh(item.status) }}</el-tag>
          <span class="time">{{ formatTime(item.created_at) }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.job-list-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.job-list-items {
  list-style: none;
  padding: 0;
  margin: 0;
}
.job-list-items li {
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  margin-bottom: 6px;
}
.job-list-items li:hover {
  background: #f5f7fa;
}
.job-list-items li.active {
  background: #ecf5ff;
  border-color: #b3d8ff;
}
.name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}
.time {
  flex: 1;
  text-align: right;
}
</style>
