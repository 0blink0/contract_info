import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import { bootstrapDesktopApp, shouldRequireOnboarding } from '@/stores/appBootstrap'
import { isValidTableKey } from '@/constants/jobSections'

let bootstrapPromise: Promise<void> | null = null

const isElectronDesktop = import.meta.env.VITE_ELECTRON === '1'

const router = createRouter({
  history: isElectronDesktop
    ? createWebHashHistory(import.meta.env.BASE_URL)
    : createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
    {
      path: '/onboarding',
      name: 'onboarding',
      component: () => import('@/views/OnboardingWizardView.vue'),
      meta: { title: '初始化向导' },
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/UploadView.vue'),
      meta: { title: '文件上传解析' },
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('@/views/FileListView.vue'),
      meta: { title: '文件列表' },
    },
    {
      path: '/kb-config',
      name: 'kb-config',
      component: () => import('@/views/KbConfigView.vue'),
      meta: { title: '知识库配置' },
    },
    {
      path: '/jobs/:id',
      component: () => import('@/layouts/JobDetailLayout.vue'),
      props: true,
      meta: { title: '文件详情' },
      children: [
        {
          path: '',
          name: 'job-hub',
          component: () => import('@/views/JobHubView.vue'),
        },
        {
          path: 'tables/:tableKey',
          name: 'job-table',
          component: () => import('@/views/JobTableView.vue'),
          beforeEnter: (to) => {
            const id = to.params.id
            const key = to.params.tableKey
            if (
              typeof id !== 'string' ||
              typeof key !== 'string' ||
              !isValidTableKey(key)
            ) {
              return {
                name: 'job-hub',
                params: { id: typeof id === 'string' ? id : '' },
              }
            }
          },
        },
        {
          path: 'field-b',
          name: 'job-field-b',
          component: () => import('@/views/JobFieldBView.vue'),
        },
      ],
    },
    {
      path: '/merge-tables',
      name: 'merge-tables',
      component: () => import('@/views/MergeTablesView.vue'),
      meta: { title: '表格合并' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { title: '系统设置' },
    },
  ],
})

router.beforeEach(async (to) => {
  if (!bootstrapPromise) bootstrapPromise = bootstrapDesktopApp()
  await bootstrapPromise
  const needsOnboarding = shouldRequireOnboarding()
  if (needsOnboarding && to.name !== 'onboarding') return { name: 'onboarding' }
  if (!needsOnboarding && to.name === 'onboarding') return { name: 'upload' }
  return true
})

export default router
