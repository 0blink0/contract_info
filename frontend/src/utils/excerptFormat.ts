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

export function excerptPreview(text: string | null | undefined, maxLen = 36): string {
  const raw = text?.trim()
  if (!raw) return '—'
  const oneLine = raw.replace(/\s+/g, ' ')
  if (oneLine.length <= maxLen) return oneLine
  return `${oneLine.slice(0, maxLen)}…`
}
