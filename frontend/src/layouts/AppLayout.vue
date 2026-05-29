<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { List, Setting, Upload } from '@element-plus/icons-vue'
import { JOB_FIELD_B, JOB_TABLE_SECTIONS } from '@/constants/jobSections'

const route = useRoute()

const activeMenu = computed(() => {
  if (route.path.startsWith('/jobs/') && route.params.id) return '/jobs'
  return route.path
})

const jobId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

const menuActive = computed(() => (jobId.value ? route.path : activeMenu.value))

const defaultOpeneds = computed(() => (jobId.value ? ['job-detail-nav'] : []))
</script>

<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="nav-aside">
      <div class="brand">
        <span class="brand-mark">CI</span>
        <div class="brand-text">
          <div class="brand-title">合同要素抽取</div>
          <div class="brand-sub">docx → Excel</div>
        </div>
      </div>
      <el-menu
        :default-active="menuActive"
        :default-openeds="defaultOpeneds"
        router
        class="nav-menu"
        background-color="transparent"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>文件上传解析</span>
        </el-menu-item>
        <el-menu-item index="/jobs" :class="{ 'jobs-parent-active': !!jobId }">
          <el-icon><List /></el-icon>
          <span>文件列表</span>
        </el-menu-item>
        <el-sub-menu v-if="jobId" index="job-detail-nav">
          <template #title>
            <span>文件详情</span>
          </template>
          <el-menu-item
            v-for="sec in JOB_TABLE_SECTIONS"
            :key="sec.key"
            :index="`/jobs/${jobId}/tables/${sec.key}`"
          >
            <span>{{ sec.label }}</span>
          </el-menu-item>
          <el-menu-item :index="`/jobs/${jobId}/field-b`">
            <span>{{ JOB_FIELD_B.label }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
  </el-container>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.nav-aside {
  background: var(--app-aside-bg);
  border-right: none;
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px 20px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-title {
  font-size: 15px;
  font-weight: 600;
  color: #f8fafc;
}

.brand-sub {
  font-size: 12px;
  color: var(--app-aside-muted);
  margin-top: 2px;
}

.nav-menu {
  border-right: none;
}

.nav-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 44px;
}

.nav-menu :deep(.el-menu-item.is-active) {
  background: rgba(59, 130, 246, 0.25) !important;
}

.nav-menu :deep(.el-menu-item.jobs-parent-active) {
  background: rgba(59, 130, 246, 0.25) !important;
  color: #ffffff !important;
}

.nav-menu :deep(.el-sub-menu__title) {
  border-radius: 8px;
  color: #cbd5e1;
}

.nav-menu :deep(.el-sub-menu .el-menu-item) {
  min-width: auto;
  padding-left: 48px !important;
  height: 40px;
}

.app-main {
  padding: 0;
  background: var(--app-bg);
  overflow: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
