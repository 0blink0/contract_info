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

export interface JobConcurrencyResponse {
  active: number
  queued: number
  max: number
}

export interface JobDetail {
  job_id: string
  filename: string
  status: string
  error_message?: string | null
  product_xlsx_path?: string | null
  fee_xlsx_path?: string | null
  lock_xlsx_path?: string | null
  share_xlsx_path?: string | null
  subscription_xlsx_path?: string | null
  path_b_available: boolean
  validation_available: boolean
  validation_fail_count: number
  validation_warn_count: number
  extraction_warnings: WarningItem[]
  extraction_warnings_count: number
  outline_preview_count?: number | null
}

export interface ProductPreviewItem {
  field: string
  value: string | null
}

export interface JobPreview {
  job_id: string
  source: string
  product_rows: ProductPreviewItem[]
  fee_columns: string[]
  fee_rows: Record<string, string | null>[]
  lock_columns: string[]
  lock_rows: Record<string, string | null>[]
  share_columns: string[]
  share_rows: Record<string, string | null>[]
  subscription_columns: string[]
  subscription_rows: Record<string, string | null>[]
}

export type PreviewSection =
  | 'product-elements'
  | 'fee-rates'
  | 'lock-periods'
  | 'share-classes'
  | 'subscription-fee-rates'

export interface JobPreviewSectionResponse {
  job_id: string
  section: PreviewSection
  source: string
  product_rows?: ProductPreviewItem[]
  fee_columns?: string[]
  fee_rows?: Record<string, string | null>[]
  lock_columns?: string[]
  lock_rows?: Record<string, string | null>[]
  lock_empty_reason?: string | null
  share_columns?: string[]
  share_rows?: Record<string, string | null>[]
  share_empty_reason?: string | null
  subscription_columns?: string[]
  subscription_rows?: Record<string, string | null>[]
}

export interface ExcerptTablePayload {
  rows: string[][]
  caption?: string | null
}

export interface VerificationRow {
  field: string
  field_label: string
  value?: string | null
  page_no?: number | null
  page_no_note?: string | null
  excerpt?: string | null
  /** Contract table block when field was taken from a docx table */
  excerpt_table?: ExcerptTablePayload | null
  excerpt_tables?: ExcerptTablePayload[] | null
  /** rule | snippet | block | table | table+narrative | narrative | value */
  capture_source?: string | null
  validation_status?: string | null
  validation_reason?: string | null
}

export interface TableVerificationResponse {
  job_id: string
  table_key: PreviewSection
  rows: VerificationRow[]
  page_no_available: boolean
}

export interface CrmHandoffItem {
  crm_field: string
  suggested_value?: string | null
  snippet?: string | null
  coverage: string
  diagnostic?: string | null
}

export interface PathBSnippetRow {
  path: string
  label: string
  text: string
}

export interface PathBResponse {
  job_id: string
  performance_fee: Record<string, unknown>
  open_day: Record<string, unknown>
  source_snippets: Record<string, string>
  source_snippet_rows: PathBSnippetRow[]
  crm_handoff: CrmHandoffItem[]
  raw_sections?: Record<string, string>
  rag_warnings?: WarningItem[]
}

export interface ValidationItem {
  field: string
  field_label?: string | null
  status: string
  value?: string | null
  evidence_text?: string | null
  reason: string
  suggestion?: string | null
}

export interface ValidationResponse {
  job_id: string
  validated_at?: string | null
  model?: string | null
  skipped: boolean
  items: ValidationItem[]
  summary: Record<string, number>
}

export interface UploadResponse {
  job_id: string
  status: string
  filename: string
}

export interface DocumentParagraph {
  index: number
  type: 'paragraph' | 'table'
  text: string
  rows?: string[][] // 仅 type==='table' 时有值
}

export interface DocumentTextResponse {
  job_id: string
  paragraph_count: number
  paragraphs: DocumentParagraph[]
}

export type DownloadKind = PreviewSection

export interface MergeSourceJob {
  job_id: string
  filename: string
}

export interface MergeRecord {
  id: string
  name: string
  table_type: string
  table_type_label: string
  source_jobs: MergeSourceJob[]
  merged_at: string
  row_count: number
  columns: string[]
}

export interface MergePreview {
  id: string
  columns: string[]
  rows: Record<string, string>[]
}
