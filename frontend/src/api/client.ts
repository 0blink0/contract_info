import type {
  DownloadKind,
  JobDetail,
  JobListResponse,
  JobPreview,
  UploadResponse,
} from './types'

const API_BASE = '/api/v1'

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
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
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

export async function listJobs(limit = 20): Promise<JobListResponse> {
  const res = await apiFetch(`/jobs?limit=${limit}`)
  return res.json()
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

export async function deleteJob(jobId: string): Promise<void> {
  await apiFetch(`/jobs/${jobId}`, { method: 'DELETE' })
}

export function downloadUrl(jobId: string, kind: DownloadKind): string {
  return `${API_BASE}/jobs/${jobId}/download/${kind}`
}

export async function downloadBlob(
  jobId: string,
  kind: DownloadKind,
  filename: string,
): Promise<void> {
  const headers = apiHeaders()
  const res = await fetch(downloadUrl(jobId, kind), { headers })
  if (!res.ok) {
    throw new Error(`下载失败: ${res.status}`)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
