import type { JobDetail } from '@/api/types'

export const MAX_UPLOAD_FILES = 20
export const MAX_PARALLEL_JOBS = 3

export interface UploadSessionJob {
  jobId: string
  filename: string
  status: string
  detail: JobDetail
}
