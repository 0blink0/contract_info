<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import JobDetail from '@/components/JobDetail.vue'

const route = useRoute()
const router = useRouter()

const jobId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

function onDeleted(id: string) {
  void router.push({ name: 'jobs' })
  if (id === jobId.value) {
    /* JobDetail clears via route change */
  }
}
</script>

<template>
  <div class="page-shell detail-page">
    <el-button class="back-btn" text @click="router.push({ name: 'jobs' })">
      ← 返回文件列表
    </el-button>
    <JobDetail
      :key="jobId ?? 'empty'"
      :job-id="jobId"
      @deleted="onDeleted"
    />
  </div>
</template>

<style scoped>
.detail-page {
  padding-top: 16px;
}

.back-btn {
  margin-bottom: 8px;
  color: #64748b;
}
</style>
