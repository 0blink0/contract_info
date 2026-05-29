import { inject, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import type { JobDetail } from '@/api/types'

export interface JobDetailContext {
  jobId: ComputedRef<string | null>
  detail: Ref<JobDetail | null>
  loading: Ref<boolean>
  status: Ref<string>
  refresh: () => Promise<void>
  activate: () => void
}

export const JOB_DETAIL_KEY: InjectionKey<JobDetailContext> = Symbol('jobDetail')

export function useJobDetailInject(): JobDetailContext {
  const ctx = inject(JOB_DETAIL_KEY)
  if (!ctx) {
    throw new Error(
      'useJobDetailInject() must be used inside JobDetailLayout (JOB_DETAIL_KEY provider missing)',
    )
  }
  return ctx
}
