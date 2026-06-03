import { ref } from 'vue'
import { getKbStatus } from '@/api/kb'

// 模块级单例，跨组件共享同一份状态
const modelLoaded = ref<boolean | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
let initialized = false

async function fetchStatus() {
  try {
    const s = await getKbStatus()
    modelLoaded.value = s.model_loaded
    if (s.model_loaded && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  } catch {
    // 忽略网络错误
  }
}

export function useKbStatus() {
  if (!initialized) {
    initialized = true
    void fetchStatus()
    // 每 10 秒轮询，加载完后自动停止
    pollTimer = setInterval(() => void fetchStatus(), 10_000)
  }

  return { modelLoaded, refresh: fetchStatus }
}
