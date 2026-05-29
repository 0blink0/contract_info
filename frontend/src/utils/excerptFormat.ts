/** Contract table block in verification excerpt (matches API ExcerptTablePayload). */
export type ExcerptTableBlock = {
  rows?: string[][]
  caption?: string | null
}

export type ExcerptEvidenceRow = {
  field: string
  excerpt?: string | null
  excerpt_table?: ExcerptTableBlock | null
  excerpt_tables?: ExcerptTableBlock[] | null
}

/** Split contract excerpt into readable paragraphs for side-panel display. */
export function formatExcerptParagraphs(text: string | null | undefined): string[] {
  const raw = text?.trim()
  if (!raw) return []

  const normalized = raw.replace(/\r\n/g, '\n')

  if (/\n\s*\n/.test(normalized)) {
    return normalized
      .split(/\n\s*\n+/)
      .map((p) => p.replace(/\n+/g, ' ').trim())
      .filter(Boolean)
  }

  if (normalized.includes('\n')) {
    return normalized
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
  }

  const sentences = normalized.split(/(?<=[。；！？])\s*/).map((s) => s.trim()).filter(Boolean)
  if (sentences.length <= 1 && normalized.length > 120) {
    const chunks: string[] = []
    let buf = ''
    for (const ch of normalized) {
      buf += ch
      if (buf.length >= 100 && /[，、；。]/.test(ch)) {
        chunks.push(buf.trim())
        buf = ''
      }
    }
    if (buf.trim()) chunks.push(buf.trim())
    return chunks.length ? chunks : [normalized]
  }

  return sentences.length ? sentences : [normalized]
}

export function excerptTablePreview(
  table: ExcerptTableBlock | null | undefined,
): string | null {
  const rows = table?.rows?.filter((r) => r?.some((c) => String(c || '').trim()))
  if (!rows?.length) return null
  const cols = Math.max(...rows.map((r) => r.length), 0)
  return `[合同表格 ${rows.length}行×${cols}列]`
}

export function excerptPreview(text: string | null | undefined, maxLen = 36): string {
  const raw = text?.trim()
  if (!raw) return '—'
  const oneLine = raw.replace(/\s+/g, ' ')
  if (oneLine.length <= maxLen) return oneLine
  return `${oneLine.slice(0, maxLen)}…`
}

export function allExcerptTables(row: {
  excerpt_tables?: ExcerptTableBlock[] | null
  excerpt_table?: ExcerptTableBlock | null
}): ExcerptTableBlock[] {
  const list = row.excerpt_tables?.filter((t) => t?.rows?.length) ?? []
  if (list.length) return list
  if (row.excerpt_table?.rows?.length) return [row.excerpt_table]
  return []
}

/** e.g. fee_rates[2].计费频率 → fee_rates[2] */
export function listTableRowKey(field: string): string | null {
  const m = field.match(/^([a-z_]+\[\d+\])\./i)
  return m ? m[1] : null
}

export function evidenceFingerprint(row: Omit<ExcerptEvidenceRow, 'field'>): string {
  const tables = allExcerptTables(row).map((t) => ({
    caption: t.caption ?? '',
    rows: t.rows ?? [],
  }))
  const excerpt = (row.excerpt ?? '').trim()
  return JSON.stringify({ tables, excerpt })
}

/** Group key: one exported table row, or unique excerpt for product-elements. */
export function evidenceGroupKey(
  field: string,
  row: Parameters<typeof evidenceFingerprint>[0],
): string {
  const listKey = listTableRowKey(field)
  if (listKey) return listKey
  return `field:${field}::${evidenceFingerprint(row)}`
}

/** Rowspan for excerpt summary column: first row in group gets count, rest 0. */
export function excerptSummaryRowspans(rows: ExcerptEvidenceRow[]): number[] {
  const spans = rows.map(() => 1)
  let i = 0
  while (i < rows.length) {
    const key = evidenceGroupKey(rows[i].field, rows[i])
    let j = i + 1
    while (j < rows.length && evidenceGroupKey(rows[j].field, rows[j]) === key) {
      j += 1
    }
    const len = j - i
    spans[i] = len
    for (let k = i + 1; k < j; k += 1) spans[k] = 0
    i = j
  }
  return spans
}

export function verificationExcerptTeaser(row: {
  excerpt?: string | null
  excerpt_table?: { rows?: string[][] } | null
  excerpt_tables?: { rows?: string[][] }[] | null
}): string {
  const tables = allExcerptTables(row)
  const tableLabels = tables
    .map((t) => excerptTablePreview(t))
    .filter((x): x is string => Boolean(x))
  const tableLabel =
    tableLabels.length > 1
      ? `[合同表格×${tableLabels.length}]`
      : tableLabels[0] ?? null
  const text = excerptPreview(row.excerpt)
  if (tableLabel && text !== '—') return `${tableLabel} · ${text}`
  if (tableLabel) return tableLabel
  return text
}
