import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
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
      path: '/jobs/:id',
      name: 'job-detail',
      component: () => import('@/views/JobDetailView.vue'),
      meta: { title: '文件详情' },
    },
  ],
})

export default router
