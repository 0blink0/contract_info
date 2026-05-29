<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { JOB_FIELD_B, JOB_TABLE_SECTIONS } from '@/constants/jobSections'

const { jobId } = useJobDetailInject()
</script>

<template>
  <div class="hub-view">
    <h3 class="section-title">任务总览</h3>
    <p class="section-desc">
      从下方进入各导入表或字段 B 专页。完整摘要与校验入口将在后续版本提供。
    </p>
    <el-row :gutter="12" class="nav-cards">
      <el-col
        v-for="sec in JOB_TABLE_SECTIONS"
        :key="sec.key"
        :xs="24"
        :sm="12"
        :md="8"
      >
        <RouterLink
          v-if="jobId"
          class="nav-card"
          :to="{ name: 'job-table', params: { id: jobId, tableKey: sec.key } }"
        >
          <span class="nav-card-label">{{ sec.label }}</span>
          <span class="nav-card-hint">进入详情 →</span>
        </RouterLink>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <RouterLink
          v-if="jobId"
          class="nav-card"
          :to="{ name: JOB_FIELD_B.routeName, params: { id: jobId } }"
        >
          <span class="nav-card-label">{{ JOB_FIELD_B.label }}</span>
          <span class="nav-card-hint">进入详情 →</span>
        </RouterLink>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.section-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.section-desc {
  margin: 0 0 20px;
  color: #64748b;
  font-size: 14px;
}

.nav-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 10px;
  border: 1px solid var(--app-border);
  background: #fff;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.nav-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
}

.nav-card-label {
  font-weight: 600;
  color: #0f172a;
}

.nav-card-hint {
  font-size: 13px;
  color: #3b82f6;
}
</style>
