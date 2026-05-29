import type {
  JobPreview,
  JobPreviewSectionResponse,
  PreviewSection,
  ProductPreviewItem,
  VerificationRow,
} from '@/api/types'

export const JOB_TABLE_SECTIONS = [
  { key: 'product-elements', label: '产品要素' },
  { key: 'fee-rates', label: '运营费率' },
  { key: 'lock-periods', label: '份额锁定期' },
  { key: 'share-classes', label: '分级份额' },
  { key: 'subscription-fee-rates', label: '申赎费率' },
] as const

export const TABLE_KEYS = JOB_TABLE_SECTIONS.map((s) => s.key)

export type TableKey = (typeof JOB_TABLE_SECTIONS)[number]['key']

export const JOB_FIELD_B = {
  label: '字段 B',
  routeName: 'job-field-b' as const,
}

const TABLE_KEY_SET = new Set<string>(TABLE_KEYS)

export function isValidTableKey(v: string): v is TableKey {
  return TABLE_KEY_SET.has(v)
}

export function sectionLabel(key: TableKey): string {
  const row = JOB_TABLE_SECTIONS.find((s) => s.key === key)
  return row?.label ?? key
}

export const TABLE_DOWNLOAD_FILES: Record<TableKey, string> = {
  'product-elements': 'product_elements.xlsx',
  'fee-rates': 'fee_rates.xlsx',
  'lock-periods': 'lock_periods.xlsx',
  'share-classes': 'share_classes.xlsx',
  'subscription-fee-rates': 'subscription_fee_rates.xlsx',
}

export type SectionKind = 'product' | 'list'

export function sectionKind(key: TableKey): SectionKind {
  return key === 'product-elements' ? 'product' : 'list'
}

const LIST_SECTION_FIELDS: Record<
  Exclude<TableKey, 'product-elements'>,
  { columns: 'fee_columns' | 'lock_columns' | 'share_columns' | 'subscription_columns'; rows: 'fee_rows' | 'lock_rows' | 'share_rows' | 'subscription_rows' }
> = {
  'fee-rates': { columns: 'fee_columns', rows: 'fee_rows' },
  'lock-periods': { columns: 'lock_columns', rows: 'lock_rows' },
  'share-classes': { columns: 'share_columns', rows: 'share_rows' },
  'subscription-fee-rates': { columns: 'subscription_columns', rows: 'subscription_rows' },
}

export function buildSectionSaveBody(
  key: TableKey,
  preview: JobPreviewSectionResponse,
): Record<string, unknown> {
  if (key === 'product-elements') {
    return { product_rows: preview.product_rows ?? [] }
  }
  const fields = LIST_SECTION_FIELDS[key]
  return {
    [fields.columns]: preview[fields.columns] ?? [],
    [fields.rows]: preview[fields.rows] ?? [],
  }
}

export function emptySectionPreview(key: TableKey, jobId: string): JobPreviewSectionResponse {
  const base = { job_id: jobId, section: key as PreviewSection, source: 'extraction' }
  if (key === 'product-elements') {
    return { ...base, product_rows: [] }
  }
  const fields = LIST_SECTION_FIELDS[key]
  return {
    ...base,
    [fields.columns]: [],
    [fields.rows]: [],
  } as JobPreviewSectionResponse
}

export function normalizeSectionPreview(
  key: TableKey,
  response: JobPreviewSectionResponse,
): JobPreviewSectionResponse {
  if (key === 'product-elements') {
    return {
      ...response,
      product_rows: response.product_rows ?? [],
    }
  }
  const fields = LIST_SECTION_FIELDS[key]
  return {
    ...response,
    [fields.columns]: response[fields.columns] ?? [],
    [fields.rows]: response[fields.rows] ?? [],
  } as JobPreviewSectionResponse
}

export const SNIPPET_DISPLAY_COLUMN = '摘录原文'

export function listTableEditableColumns(
  columns: string[],
  rows: Record<string, string | null>[],
): string[] {
  if (columns.length) {
    return columns.filter((c) => c !== SNIPPET_DISPLAY_COLUMN)
  }
  if (!rows.length) return []
  return Object.keys(rows[0]).filter((c) => c !== SNIPPET_DISPLAY_COLUMN)
}

export function listSectionData(preview: JobPreviewSectionResponse, key: TableKey) {
  const fields = LIST_SECTION_FIELDS[key as Exclude<TableKey, 'product-elements'>]
  const columns = (preview[fields.columns] as string[] | undefined) ?? []
  const rows = (preview[fields.rows] as Record<string, string | null>[] | undefined) ?? []
  return { columns, rows }
}

export function productRows(preview: JobPreviewSectionResponse): ProductPreviewItem[] {
  return preview.product_rows ?? []
}

export function sectionRowCount(
  key: TableKey,
  preview: JobPreviewSectionResponse,
): number {
  if (key === 'product-elements') {
    return preview.product_rows?.length ?? 0
  }
  const { rows } = listSectionData(preview, key)
  return rows.length
}

/** Slice full preview (legacy GET /preview) into a sectional response. */
export function slicePreviewSection(
  full: JobPreview,
  section: PreviewSection,
): JobPreviewSectionResponse {
  const base: JobPreviewSectionResponse = {
    job_id: full.job_id,
    section,
    source: full.source,
  }
  switch (section) {
    case 'product-elements':
      return { ...base, product_rows: full.product_rows }
    case 'fee-rates':
      return {
        ...base,
        fee_columns: full.fee_columns,
        fee_rows: full.fee_rows,
      }
    case 'lock-periods':
      return {
        ...base,
        lock_columns: full.lock_columns,
        lock_rows: full.lock_rows,
      }
    case 'share-classes':
      return {
        ...base,
        share_columns: full.share_columns,
        share_rows: full.share_rows,
      }
    case 'subscription-fee-rates':
      return {
        ...base,
        subscription_columns: full.subscription_columns,
        subscription_rows: full.subscription_rows,
      }
    default:
      return base
  }
}

/** Merge sectional PUT body into full preview for legacy save endpoint. */
type JobPreviewUpdatePayload = Omit<JobPreview, 'job_id' | 'source'>

const PAGE_UNAVAILABLE_NOTE = '页码暂未解析'

/** Build核对 rows from sectional preview when verification API is missing or empty. */
export function verificationRowsFromSectionPreview(
  section: JobPreviewSectionResponse,
  tableKey: TableKey,
): VerificationRow[] {
  if (tableKey === 'product-elements') {
    return (section.product_rows ?? []).map((r) => ({
      field: r.field,
      field_label: r.field,
      value: r.value ?? null,
      page_no: null,
      page_no_note: PAGE_UNAVAILABLE_NOTE,
      excerpt: null,
    }))
  }
  const { columns, rows } = listSectionData(section, tableKey)
  const out: VerificationRow[] = []
  rows.forEach((row, i) => {
    const excerptRaw = row[SNIPPET_DISPLAY_COLUMN]
    const excerpt =
      typeof excerptRaw === 'string' && excerptRaw.trim() ? excerptRaw.trim() : null
    const cols = columns.length ? columns : Object.keys(row)
    for (const col of cols) {
      if (col === SNIPPET_DISPLAY_COLUMN) continue
      out.push({
        field: `${tableKey}[${i}].${col}`,
        field_label: col,
        value: row[col] ?? null,
        page_no: null,
        page_no_note: PAGE_UNAVAILABLE_NOTE,
        excerpt,
      })
    }
  })
  return out
}

/** Backend verification `field` paths: fee_rates[0].运营费类型 or product field name. */
export function parseVerificationFieldPath(
  field: string,
): { index: number; extractionKey: string } | { productField: string } | null {
  const listMatch = field.match(/^([a-z_]+)\[(\d+)\]\.(.+)$/i)
  if (listMatch) {
    return {
      index: Number(listMatch[2]),
      extractionKey: listMatch[3],
    }
  }
  if (field && !field.includes('[')) {
    return { productField: field }
  }
  return null
}

/** Apply核对表字段值 edits onto sectional preview before PUT /preview/{section}. */
export function applyVerificationRowsToPreview(
  tableKey: TableKey,
  preview: JobPreviewSectionResponse,
  rows: VerificationRow[],
): JobPreviewSectionResponse {
  const next = structuredClone(preview) as JobPreviewSectionResponse
  for (const row of rows) {
    const value = row.value ?? ''
    const parsed = parseVerificationFieldPath(row.field)
    if (!parsed) continue
    if ('productField' in parsed) {
      const items = next.product_rows ?? []
      const item = items.find((r) => r.field === parsed.productField)
      if (item) item.value = value
      continue
    }
    const { rows: listRows } = listSectionData(next, tableKey)
    const target = listRows[parsed.index]
    if (!target) continue
    const col = row.field_label || parsed.extractionKey
    target[col] = value
  }
  return next
}

export function mergeSectionIntoFullPreview(
  full: JobPreview,
  section: PreviewSection,
  body: Record<string, unknown>,
): JobPreviewUpdatePayload {
  const payload: JobPreviewUpdatePayload = {
    product_rows: full.product_rows,
    fee_columns: full.fee_columns,
    fee_rows: full.fee_rows,
    lock_columns: full.lock_columns,
    lock_rows: full.lock_rows,
    share_columns: full.share_columns,
    share_rows: full.share_rows,
    subscription_columns: full.subscription_columns,
    subscription_rows: full.subscription_rows,
  }
  if (section === 'product-elements') {
    payload.product_rows = (body.product_rows as ProductPreviewItem[] | undefined) ?? full.product_rows
    return payload
  }
  const fields = LIST_SECTION_FIELDS[section]
  payload[fields.columns] = (body[fields.columns] as string[] | undefined) ?? full[fields.columns]
  payload[fields.rows] =
    (body[fields.rows] as Record<string, string | null>[] | undefined) ?? full[fields.rows]
  return payload
}
