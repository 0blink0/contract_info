export type StepState = 'wait' | 'process' | 'finish' | 'error'

export interface StepView {
  label: string
  state: StepState
}

const STEPS = ['解析', '抽取', '导出'] as const

const IN_PROGRESS = new Set(['parsing', 'extracting', 'exporting'])

/** 流水线任一阶段（含阶段间隙 parsed/extracted） */
const PIPELINE_ACTIVE = new Set([
  'queued',
  'parsing',
  'parsed',
  'extracting',
  'extracted',
  'exporting',
])

const STATUS_ZH: Record<string, string> = {
  pending: '待处理',
  queued: '排队中',
  parsing: '解析中',
  parsed: '已解析',
  extracting: '抽取中',
  extracted: '已抽取',
  exporting: '导出中',
  exported: '已完成',
  failed: '解析失败',
  extraction_failed: '抽取失败',
  export_failed: '导出失败',
}

export function statusLabelZh(status: string): string {
  return STATUS_ZH[status] ?? status
}

export function isInProgress(status: string): boolean {
  return IN_PROGRESS.has(status)
}

export function isPipelineActive(status: string): boolean {
  return PIPELINE_ACTIVE.has(status)
}

export function canStartRun(status: string): boolean {
  return ['pending', 'failed', 'parsed', 'extraction_failed', 'extracted', 'export_failed'].includes(
    status,
  )
}

export function isQueued(status: string): boolean {
  return status === 'queued'
}

export function canRetry(status: string): boolean {
  return ['failed', 'extraction_failed', 'export_failed'].includes(status)
}

export function stepStates(status: string): StepView[] {
  const base = (): StepView[] => STEPS.map((label) => ({ label, state: 'wait' as StepState }))

  switch (status) {
    case 'pending':
    case 'queued':
      return base()
    case 'parsing':
      return [
        { label: STEPS[0], state: 'process' },
        { label: STEPS[1], state: 'wait' },
        { label: STEPS[2], state: 'wait' },
      ]
    case 'parsed':
      return [
        { label: STEPS[0], state: 'finish' },
        { label: STEPS[1], state: 'wait' },
        { label: STEPS[2], state: 'wait' },
      ]
    case 'extracting':
      return [
        { label: STEPS[0], state: 'finish' },
        { label: STEPS[1], state: 'process' },
        { label: STEPS[2], state: 'wait' },
      ]
    case 'extracted':
      return [
        { label: STEPS[0], state: 'finish' },
        { label: STEPS[1], state: 'finish' },
        { label: STEPS[2], state: 'wait' },
      ]
    case 'exporting':
      return [
        { label: STEPS[0], state: 'finish' },
        { label: STEPS[1], state: 'finish' },
        { label: STEPS[2], state: 'process' },
      ]
    case 'exported':
      return STEPS.map((label) => ({ label, state: 'finish' as StepState }))
    case 'failed':
      return [
        { label: STEPS[0], state: 'error' },
        { label: STEPS[1], state: 'wait' },
        { label: STEPS[2], state: 'wait' },
      ]
    case 'extraction_failed':
      return [
        { label: STEPS[0], state: 'finish' },
        { label: STEPS[1], state: 'error' },
        { label: STEPS[2], state: 'wait' },
      ]
    case 'export_failed':
      return [
        { label: STEPS[0], state: 'finish' },
        { label: STEPS[1], state: 'finish' },
        { label: STEPS[2], state: 'error' },
      ]
    default:
      return base()
  }
}
