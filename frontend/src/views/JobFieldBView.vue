<script setup lang="ts">
import { computed } from 'vue'
import PathBDetail from '@/components/pathb/PathBDetail.vue'
import { useJobDetailInject } from '@/composables/useJobDetailContext'
import { JOB_FIELD_B } from '@/constants/jobSections'

const { jobId, detail } = useJobDetailInject()

const available = computed(() => Boolean(detail.value?.path_b_available))
</script>

<template>
  <div class="field-b-view">
    <h3 class="section-title">{{ JOB_FIELD_B.label }}</h3>
    <PathBDetail
      v-if="jobId"
      :job-id="jobId"
      :available="available"
      :auto-load="true"
    />
    <el-empty v-else description="无效的任务" />
  </div>
</template>

<style scoped>
.section-title {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
}
</style>
