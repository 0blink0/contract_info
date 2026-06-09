import type {
  DocumentTextResponse,
  DownloadKind,
  JobConcurrencyResponse,
  JobDetail,
  JobListResponse,
  JobPreview,
  JobPreviewSectionResponse,
  MergePreview,
  MergeRecord,
  PathBResponse,
  PreviewSection,
  TableVerificationResponse,
  UploadResponse,
  ValidationResponse,
} from './types'
import { getApiBase } from '@/stores/appBootstrap'
import {
  mergeSectionIntoFullPreview,
  slicePreviewSection,
  verificationRowsFromSectionPreview,
} from '@/constants/jobSections'
import type { TableKey } from '@/constants/jobSections'

function apiHeaders(): HeadersInit {
  const headers: HeadersInit = {}
  const key = import.meta.env.VITE_API_KEY
  if (key) {
    headers['X-API-Key'] = key
  }
  return headers
}

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers)
  for (const [k, v] of Object.entries(apiHeaders())) {
    headers.set(k, v as string)
  }
  const response = await fetch(`${getApiBase()}${path}`, { ...options, headers })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response
}

export { apiFetch }

export async function listJobs(limit = 20): Promise<JobListResponse> {
  const res = await apiFetch(`/jobs?limit=${limit}`)
  return res.json()
}

export async function getJobConcurrency(): Promise<JobConcurrencyResponse> {
  const res = await apiFetch('/jobs/concurrency')
  return res.json()
}

export function isNotFoundError(e: unknown): boolean {
  if (!(e instanceof Error)) return false
  const msg = e.message.trim()
  return msg === 'Not Found' || /\b404\b/.test(msg)
}

/** Extract human-readable message from API errors (including 409 detail objects). */
export function parseApiError(e: unknown): string {
  if (!(e instanceof Error)) return '操作失败'
  const raw = e.message
  try {
    const parsed = JSON.parse(raw) as { detail?: string | { detail?: string } }
    if (typeof parsed.detail === 'string') return parsed.detail
    if (parsed.detail && typeof parsed.detail === 'object' && 'detail' in parsed.detail) {
      const inner = parsed.detail.detail
      if (typeof inner === 'string') return inner
    }
  } catch {
    /* not JSON */
  }
  return raw || '操作失败'
}

export async function getJob(jobId: string): Promise<JobDetail> {
  const res = await apiFetch(`/jobs/${jobId}`)
  return res.json()
}

export type { JobPreview } from './types'

export async function getJobPreview(jobId: string): Promise<JobPreview> {
  const res = await apiFetch(`/jobs/${jobId}/preview`)
  return res.json()
}

export async function getPathB(jobId: string): Promise<PathBResponse> {
  const res = await apiFetch(`/jobs/${jobId}/path-b`)
  return res.json()
}

export async function getValidation(jobId: string): Promise<ValidationResponse> {
  const res = await apiFetch(`/jobs/${jobId}/validation`)
  return res.json()
}

export type JobPreviewUpdatePayload = Omit<JobPreview, 'job_id' | 'source'>

export async function saveJobPreview(
  jobId: string,
  payload: JobPreviewUpdatePayload,
): Promise<JobPreview> {
  const res = await apiFetch(`/jobs/${jobId}/preview`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}

export async function getJobPreviewSection(
  jobId: string,
  section: PreviewSection,
): Promise<JobPreviewSectionResponse> {
  try {
    const res = await apiFetch(`/jobs/${jobId}/preview/${section}`)
    return res.json()
  } catch (e) {
    if (!isNotFoundError(e)) throw e
    const full = await getJobPreview(jobId)
    return slicePreviewSection(full, section)
  }
}

export async function saveJobPreviewSection(
  jobId: string,
  section: PreviewSection,
  body: Record<string, unknown>,
): Promise<JobPreviewSectionResponse> {
  try {
    const res = await apiFetch(`/jobs/${jobId}/preview/${section}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return res.json()
  } catch (e) {
    if (!isNotFoundError(e)) throw e
    const full = await getJobPreview(jobId)
    const merged = mergeSectionIntoFullPreview(full, section, body)
    const saved = await saveJobPreview(jobId, merged)
    return slicePreviewSection(saved, section)
  }
}

async function verificationWithPreviewFallback(
  jobId: string,
  tableKey: PreviewSection,
  partial: TableVerificationResponse,
): Promise<TableVerificationResponse> {
  if (partial.rows?.length) {
    return partial
  }
  const section = await getJobPreviewSection(jobId, tableKey)
  const rows = verificationRowsFromSectionPreview(section, tableKey as TableKey)
  return {
    ...partial,
    rows,
    page_no_available: partial.page_no_available && rows.some((r) => r.page_no != null),
  }
}

export async function getTableVerification(
  jobId: string,
  tableKey: PreviewSection,
): Promise<TableVerificationResponse> {
  const empty = (): TableVerificationResponse => ({
    job_id: jobId,
    table_key: tableKey,
    rows: [],
    page_no_available: false,
  })
  try {
    const res = await apiFetch(`/jobs/${jobId}/verification/${tableKey}`)
    const data = (await res.json()) as TableVerificationResponse
    return verificationWithPreviewFallback(jobId, tableKey, data)
  } catch (e) {
    if (!isNotFoundError(e)) throw e
    return verificationWithPreviewFallback(jobId, tableKey, empty())
  }
}

export async function getDocumentText(jobId: string): Promise<DocumentTextResponse> {
  const res = await apiFetch(`/jobs/${jobId}/document-text`)
  return res.json()
}

export async function upload(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiFetch('/upload', { method: 'POST', body: form })
  return res.json()
}

export async function runJob(jobId: string): Promise<{ job_id: string; status: string }> {
  const res = await apiFetch(`/jobs/${jobId}/run`, { method: 'POST' })
  return res.json()
}

export async function reextractProduct(jobId: string): Promise<{ job_id: string; status: string }> {
  const res = await apiFetch(`/jobs/${jobId}/reextract-product`, { method: 'POST' })
  return res.json()
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiFetch(`/jobs/${jobId}`, { method: 'DELETE' })
}

export function downloadUrl(jobId: string, kind: DownloadKind): string {
  return `${getApiBase()}/jobs/${jobId}/download/${kind}`
}

export async function createMerge(
  jobIds: string[],
  tableType: string,
  name = '',
): Promise<MergeRecord> {
  const res = await apiFetch('/merge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: jobIds, table_type: tableType, name }),
  })
  return res.json()
}

export async function listMerges(): Promise<MergeRecord[]> {
  const res = await apiFetch('/merge')
  return res.json()
}

export async function getMergePreview(mergeId: string): Promise<MergePreview> {
  const res = await apiFetch(`/merge/${mergeId}/preview`)
  return res.json()
}

export function mergeDownloadUrl(mergeId: string): string {
  return `${getApiBase()}/merge/${mergeId}/download`
}

export async function downloadMergeBlob(mergeId: string, filename: string): Promise<void> {
  const headers = apiHeaders()
  const res = await fetch(mergeDownloadUrl(mergeId), { headers })
  if (!res.ok) throw new Error(`下载失败: ${res.status}`)
  const blob = await res.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = filename
  a.click()
  URL.revokeObjectURL(objUrl)
}

export async function appendToMerge(mergeId: string, jobIds: string[]): Promise<MergeRecord> {
  const res = await apiFetch(`/merge/${mergeId}/append`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: jobIds }),
  })
  return res.json()
}

export async function deleteMergeRecord(mergeId: string): Promise<void> {
  await apiFetch(`/merge/${mergeId}`, { method: 'DELETE' })
}

export async function deleteAllMergeRecords(): Promise<number> {
  const res = await apiFetch('/merge/all', { method: 'DELETE' })
  const data = (await res.json()) as { deleted: number }
  return data.deleted
}


export async function downloadBlob(
  jobId: string,
  kind: DownloadKind | 'review-report',
  filename: string,
): Promise<void> {
  const headers = apiHeaders()
  const url = kind === 'review-report'
    ? `${getApiBase()}/jobs/${jobId}/download/review-report`
    : downloadUrl(jobId, kind as DownloadKind)
  const res = await fetch(url, { headers })
  if (!res.ok) {
    throw new Error(`下载失败: ${res.status}`)
  }
  const blob = await res.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = filename
  a.click()
  URL.revokeObjectURL(objUrl)
}
