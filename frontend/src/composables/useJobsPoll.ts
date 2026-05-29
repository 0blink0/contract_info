import { onUnmounted } from 'vue'
import { getJob } from '@/api/client'
import type { JobDetail } from '@/api/types'

const POLL_MS = 2000

const TERMINAL = new Set([
  'exported',
  'failed',
  'extraction_failed',
  'export_failed',
])

const PIPELINE_POLL = new Set([
  'parsing',
  'parsed',
  'extracting',
  'extracted',
  'exporting',
])

type UpdateHandler = (detail: JobDetail) => void

interface RegistryEntry {
  status: string
  forcePoll: boolean
  onUpdate: UpdateHandler
}

export function createJobsPoll() {
  const registry = new Map<string, RegistryEntry>()
  let timer: ReturnType<typeof setInterval> | null = null

  function shouldPoll(entry: RegistryEntry): boolean {
    if (TERMINAL.has(entry.status)) {
      entry.forcePoll = false
      return false
    }
    if (entry.forcePoll) return true
    return PIPELINE_POLL.has(entry.status)
  }

  function anyPolling(): boolean {
    for (const entry of registry.values()) {
      if (shouldPoll(entry)) return true
    }
    return false
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function start() {
    stop()
    if (!anyPolling()) return
    void tick()
    timer = setInterval(() => void tick(), POLL_MS)
  }

  async function tick() {
    const ids = [...registry.keys()].filter((id) => {
      const entry = registry.get(id)
      return entry && shouldPoll(entry)
    })
    if (!ids.length) {
      stop()
      return
    }
    await Promise.all(
      ids.map(async (id) => {
        const entry = registry.get(id)
        if (!entry) return
        try {
          const detail = await getJob(id)
          entry.status = detail.status
          entry.onUpdate(detail)
          if (TERMINAL.has(detail.status)) {
            entry.forcePoll = false
          }
        } catch {
          /* transient */
        }
      }),
    )
    if (!anyPolling()) stop()
  }

  function register(jobId: string, initialStatus: string, onUpdate: UpdateHandler) {
    registry.set(jobId, {
      status: initialStatus,
      forcePoll: false,
      onUpdate,
    })
    start()
  }

  function unregister(jobId: string) {
    registry.delete(jobId)
    if (!anyPolling()) stop()
  }

  function activate(jobId: string) {
    const entry = registry.get(jobId)
    if (!entry) return
    entry.forcePoll = true
    start()
  }

  onUnmounted(stop)

  return { register, unregister, activate, refresh: tick, stop }
}
