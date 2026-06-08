<script setup lang="ts">
import { computed } from 'vue'
import HubSectionCard from '@/components/hub/HubSectionCard.vue'
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { useHubSummary } from '@/composables/useHubSummary'
import { JOB_FIELD_B } from '@/constants/jobSections'

const { jobId, detail } = useJobDetailInject()

const {
  tableSummaries,
  pathBSummary,
  pathBLoading,
  canLoadSummaries,
  reload,
} = useHubSummary()

const validationWarn = computed(() => detail.value?.validation_warn_count ?? 0)

function tableSubtitle(rowCount: number | null, loading: boolean): string {
  if (loading) return '加载中…'
  if (!canLoadSummaries.value) return '尚未抽取'
  if (rowCount === null) return '—'
  return `${rowCount} 行`
}
</script>

<template>
  <div class="hub-view">
    <div class="hub-header">
      <h3 class="section-title">任务总览</h3>
      <div class="hub-header-tags">
        <el-tag v-if="validationWarn > 0" type="warning" size="small">
          校验 warn {{ validationWarn }}
        </el-tag>
        <el-button
          v-if="canLoadSummaries"
          size="small"
          text
          type="primary"
          @click="reload"
        >
          刷新摘要
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!canLoadSummaries"
      type="info"
      :closable="false"
      show-icon
      title="抽取完成后可查看各表行数摘要"
      class="status-alert"
    />

    <el-row :gutter="12" class="summary-cards">
      <el-col
        v-for="row in tableSummaries"
        :key="row.key"
        :xs="24"
        :sm="12"
        :md="8"
      >
        <HubSectionCard
          v-if="jobId"
          :title="row.label"
          :subtitle="tableSubtitle(row.rowCount, row.loading)"
          :loading="row.loading"
          :to="{ name: 'job-table', params: { id: jobId, tableKey: row.key } }"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <HubSectionCard
          v-if="jobId"
          :title="JOB_FIELD_B.label"
          :subtitle="
            pathBLoading
              ? '加载中…'
              : pathBSummary ?? (detail?.path_b_available ? '—' : '暂无开放日/业绩报酬')
          "
          :loading="pathBLoading"
          :to="{ name: JOB_FIELD_B.routeName, params: { id: jobId } }"
        />
      </el-col>
    </el-row>

  </div>
</template>

<style scoped>
.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.hub-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.hub-header-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-alert {
  margin-bottom: 16px;
}

.summary-cards {
  margin-bottom: 20px;
}


</style>
