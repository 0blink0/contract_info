<script setup lang="ts">
import { ref, watch } from 'vue'
import PathBDetail from '@/components/pathb/PathBDetail.vue'

const props = defineProps<{
  jobId: string | null
  available: boolean
  visible: boolean
}>()

const activeNames = ref<string[]>([])
const detailRef = ref<InstanceType<typeof PathBDetail> | null>(null)

watch(
  () => props.jobId,
  () => {
    activeNames.value = []
  },
)

async function onExpand(names: string | string[]) {
  const open = Array.isArray(names) ? names.length > 0 : Boolean(names)
  if (open && props.available && props.jobId) {
    await detailRef.value?.load()
  }
}
</script>

<template>
  <div v-if="visible" class="path-b-panel">
    <el-collapse v-model="activeNames" @change="onExpand">
      <el-collapse-item name="pathb">
        <template #title>
          <span class="panel-title">路径 B（需 CRM 手录）</span>
          <el-text type="info" size="small" class="panel-hint">
            业绩报酬 / 开放日 — 不进 Excel 导入母版
          </el-text>
        </template>
        <PathBDetail
          v-if="jobId"
          ref="detailRef"
          :job-id="jobId"
          :available="available"
          :auto-load="false"
        />
        <el-empty v-else description="暂无任务" />
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.path-b-panel {
  margin-bottom: 12px;
}
.panel-title {
  font-weight: 600;
  margin-right: 8px;
}
.panel-hint {
  margin-left: 4px;
}
</style>
