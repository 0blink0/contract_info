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
  table: { rows?: string[][] } | null | undefined,
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
  excerpt_tables?: { rows?: string[][] }[] | null
  excerpt_table?: { rows?: string[][] } | null
}): { rows?: string[][] }[] {
  const list = row.excerpt_tables?.filter((t) => t?.rows?.length) ?? []
  if (list.length) return list
  if (row.excerpt_table?.rows?.length) return [row.excerpt_table]
  return []
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
