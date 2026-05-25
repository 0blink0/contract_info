<script setup lang="ts">
import { computed } from 'vue'
import { stepStates } from '@/constants/status'

const props = defineProps<{ status: string }>()

const steps = computed(() => stepStates(props.status))
</script>

<template>
  <el-steps :active="999" align-center finish-status="success" class="process-steps">
    <el-step
      v-for="(step, i) in steps"
      :key="i"
      :title="step.label"
      :status="
        step.state === 'error'
          ? 'error'
          : step.state === 'process'
            ? 'process'
            : step.state === 'finish'
              ? 'success'
              : 'wait'
      "
    />
  </el-steps>
</template>

<style scoped>
.process-steps {
  margin: 16px 0;
}
</style>
