import { apiFetch } from '@/api/client'

export interface KbEntryInput {
  field_name: string
  field_value: string
  snippet: string
  source_job_id: string
  source_filename: string
}

export interface KbEntriesRequest {
  entries: KbEntryInput[]
}

export interface KbEntriesResponse {
  ids: string[]
  count: number
}

export interface KbEntryItem {
  id: string
  field_name: string
  field_value: string
  snippet: string
  source_job_id: string
  source_filename: string
  created_at: string
}

export interface KbListResponse {
  items: KbEntryItem[]
  total: number
}

export async function postKbEntries(body: KbEntriesRequest): Promise<KbEntriesResponse> {
  const res = await apiFetch('/kb/entries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json()
}

export interface GetKbEntriesParams {
  field_name?: string
  page?: number
  page_size?: number
}

export async function getKbEntries(params: GetKbEntriesParams = {}): Promise<KbListResponse> {
  const query = new URLSearchParams()
  if (params.field_name && params.field_name.trim()) query.set('field_name', params.field_name.trim())
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 20))
  const qs = query.toString()
  const path = qs ? `/kb/entries?${qs}` : '/kb/entries'
  const res = await apiFetch(path)
  return res.json()
}

export async function deleteKbEntry(id: string): Promise<void> {
  await apiFetch(`/kb/entries/${id}`, { method: 'DELETE' })
}
