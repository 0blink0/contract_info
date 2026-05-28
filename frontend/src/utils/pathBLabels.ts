/** 路径 B source_snippets 字段路径 → 中文（与 backend field_labels 对齐） */

const PATH_B: Record<string, string> = {
  'performance_fee.extraction_method': '业绩报酬·提取方式',
  'performance_fee.benchmark_type': '业绩报酬·基准类型',
  'performance_fee.hurdle_nav': '业绩报酬·门槛净值类型',
  'performance_fee.extraction_timing': '业绩报酬·提取时点',
  'performance_fee.summary': '业绩报酬·合同摘要',
  'performance_fee.manager_waiver': '业绩报酬·管理人放弃提取',
  'open_day.fixed_schedule': '开放日·固定安排',
  'open_day.open_business': '开放日·开放业务',
  'open_day.temporary_open': '开放日·临时开放',
  'open_day.ad_hoc_rules': '开放日·特殊规则',
}

const TIER_FIELD: Record<string, string> = {
  ratio_pct: '计提比例',
  description: '档位说明',
  benchmark: '比较基准',
  threshold: '计提门槛',
}

const TIER_RE = /^performance_fee\.tiers\[(\d+)\]\.(\w+)$/

type PathBLike = {
  performance_fee?: { tiers?: Array<{ share_class?: string }> }
}

export function labelForPathBSnippet(path: string, pathB?: PathBLike | null): string {
  const text = (path || '').trim()
  if (!text) return text
  if (PATH_B[text]) return PATH_B[text]
  const m = TIER_RE.exec(text)
  if (m) {
    const tierIdx = Number(m[1])
    const sub = TIER_FIELD[m[2]] ?? m[2]
    const tiers = pathB?.performance_fee?.tiers
    const share = tiers?.[tierIdx]?.share_class
    if (share) return `业绩报酬·${String(share).toUpperCase()}类·${sub}`
    return `业绩报酬·第${tierIdx + 1}档·${sub}`
  }
  const parts = text.split('.')
  if (parts.length >= 2) {
    const module = parts[0] === 'performance_fee' ? '业绩报酬' : '开放日'
    return `${module}·${parts[parts.length - 1]}`
  }
  return text
}
