<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  title: string
  subtitle: string
  to: { name: string; params: Record<string, string> }
  loading?: boolean
  failCount?: number
  warnCount?: number
}>()
</script>

<template>
  <RouterLink class="hub-card" :to="to">
    <div class="hub-card-head">
      <span class="hub-card-label">{{ title }}</span>
      <span v-if="failCount && failCount > 0" class="hub-badge fail">fail {{ failCount }}</span>
      <span v-if="warnCount && warnCount > 0" class="hub-badge warn">warn {{ warnCount }}</span>
    </div>
    <span class="hub-card-sub">
      <el-skeleton v-if="loading" animated :rows="0" style="width: 80px; height: 14px" />
      <template v-else>{{ subtitle }}</template>
    </span>
    <span class="hub-card-hint">进入详情 →</span>
  </RouterLink>
</template>

<style scoped>
.hub-card {
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
  min-height: 100px;
}

.hub-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
}

.hub-card-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.hub-card-label {
  font-weight: 600;
  color: #0f172a;
}

.hub-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.hub-badge.fail {
  background: #fee2e2;
  color: #b91c1c;
}

.hub-badge.warn {
  background: #fef3c7;
  color: #b45309;
}

.hub-card-sub {
  font-size: 13px;
  color: #64748b;
}

.hub-card-hint {
  font-size: 13px;
  color: #3b82f6;
  margin-top: auto;
}
</style>
