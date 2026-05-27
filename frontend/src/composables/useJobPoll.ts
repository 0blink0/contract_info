import { onUnmounted, ref, watch, type Ref } from 'vue'
import { getJob } from '@/api/client'
import type { JobDetail } from '@/api/types'

const POLL_MS = 2000

const TERMINAL = new Set([
  'exported',
  'failed',
  'extraction_failed',
  'export_failed',
])

/** Backend may advance the pipeline through these between in_progress flags. */
const PIPELINE_POLL = new Set([
  'parsing',
  'parsed',
  'extracting',
  'extracted',
  'exporting',
])

export function useJobPoll(
  jobId: Ref<string | null>,
  status: Ref<string>,
  onUpdate: (detail: JobDetail) => void,
) {
  let timer: ReturnType<typeof setInterval> | null = null
  const forcePoll = ref(false)

  function shouldPoll(): boolean {
    if (!jobId.value) return false
    if (TERMINAL.has(status.value)) {
      forcePoll.value = false
      return false
    }
    if (forcePoll.value) return true
    return PIPELINE_POLL.has(status.value)
  }

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
      if (TERMINAL.has(detail.status)) {
        forcePoll.value = false
        stop()
      }
    } catch {
      /* keep polling on transient errors */
    }
  }

  function start() {
    stop()
    if (!shouldPoll()) return
    void tick()
    timer = setInterval(() => void tick(), POLL_MS)
  }

  /** Call after POST /run — API may still return pending before background work starts. */
  function activate() {
    forcePoll.value = true
    start()
  }

  watch(
    [jobId, status, forcePoll],
    () => {
      if (shouldPoll()) start()
      else stop()
    },
    { immediate: true },
  )

  onUnmounted(stop)

  return { stop, refresh: tick, activate }
}
