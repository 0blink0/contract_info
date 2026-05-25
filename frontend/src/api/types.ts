export interface WarningItem {
  field: string
  code: string
  message: string
  suggestion?: string | null
}

export interface JobListItem {
  job_id: string
  filename: string
  status: string
  created_at: string
}

export interface JobListResponse {
  items: JobListItem[]
}

export interface JobDetail {
  job_id: string
  filename: string
  status: string
  error_message?: string | null
  product_xlsx_path?: string | null
  fee_xlsx_path?: string | null
  extraction_warnings: WarningItem[]
  extraction_warnings_count: number
  outline_preview_count?: number | null
}

export interface UploadResponse {
  job_id: string
  status: string
  filename: string
}

export type DownloadKind = 'product-elements' | 'fee-rates'
