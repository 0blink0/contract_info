import { onUnmounted, watch, type Ref } from 'vue'
import { getJob } from '@/api/client'
import type { JobDetail } from '@/api/types'

const POLL_MS = 2500

export function useJobPoll(
  jobId: Ref<string | null>,
  status: Ref<string>,
  onUpdate: (detail: JobDetail) => void,
) {
  let timer: ReturnType<typeof setInterval> | null = null

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  async function tick() {
    if (!jobId.value) return
    try {
      const detail = await getJob(jobId.value)
      onUpdate(detail)
      status.value = detail.status
      if (!['parsing', 'extracting', 'exporting'].includes(detail.status)) {
        stop()
      }
    } catch {
      /* keep polling on transient errors */
    }
  }

  function start() {
    stop()
    if (!jobId.value) return
    if (!['parsing', 'extracting', 'exporting'].includes(status.value)) return
    timer = setInterval(() => void tick(), POLL_MS)
  }

  watch(
    [jobId, status],
    () => {
      if (jobId.value && ['parsing', 'extracting', 'exporting'].includes(status.value)) {
        start()
      } else {
        stop()
      }
    },
    { immediate: true },
  )

  onUnmounted(stop)

  return { stop, refresh: tick }
}
