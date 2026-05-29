import { computed, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getPathB } from '@/api/client'
import type { PathBResponse } from '@/api/types'

const rawSectionLabels: Record<string, string> = {
  performance_fee: '业绩报酬条款原文',
  open_day: '申购赎回 / 开放日条款原文',
}

export function usePathB(jobId: Ref<string | null>) {
  const loaded = ref(false)
  const loading = ref(false)
  const data = ref<PathBResponse | null>(null)
  const showJson = ref(false)

  const crmRows = computed(() => data.value?.crm_handoff ?? [])

  const snippetRows = computed(() => data.value?.source_snippet_rows ?? [])

  const rawSections = computed(() => {
    const sections = data.value?.raw_sections
    if (!sections) return []
    return Object.entries(sections)
      .filter(([, text]) => text && text.trim())
      .map(([key, text]) => ({
        key,
        label: rawSectionLabels[key] ?? key,
        text: text.trim(),
      }))
  })

  const tierRows = computed(() => {
    const tiers = data.value?.performance_fee?.tiers
    return Array.isArray(tiers) ? tiers : []
  })

  const filledCount = computed(() =>
    crmRows.value.filter((r) => r.suggested_value && r.coverage !== 'missing').length,
  )

  const jsonText = computed(() =>
    data.value ? JSON.stringify(data.value, null, 2) : '',
  )

  function coverageLabel(c: string) {
    if (c === 'full') return '可直接填'
    if (c === 'partial') return '建议核对'
    return '需手录'
  }

  function coverageTagType(c: string) {
    if (c === 'full') return 'success'
    if (c === 'partial') return 'warning'
    return 'info'
  }

  async function load(force = false) {
    if (!jobId.value || (loaded.value && !force)) return
    loading.value = true
    try {
      data.value = await getPathB(jobId.value)
      loaded.value = true
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '路径 B 加载失败')
    } finally {
      loading.value = false
    }
  }

  async function refresh() {
    loaded.value = false
    await load(true)
  }

  async function copyJson() {
    if (!jsonText.value) return
    try {
      await navigator.clipboard.writeText(jsonText.value)
      ElMessage.success('已复制 JSON')
    } catch {
      ElMessage.error('复制失败')
    }
  }

  function downloadJson() {
    if (!jobId.value || !jsonText.value) return
    const blob = new Blob([jsonText.value], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `path_b_${jobId.value}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  function reset() {
    loaded.value = false
    loading.value = false
    data.value = null
    showJson.value = false
  }

  watch(jobId, () => reset())

  return {
    data,
    loading,
    loaded,
    showJson,
    crmRows,
    snippetRows,
    rawSections,
    tierRows,
    filledCount,
    jsonText,
    coverageLabel,
    coverageTagType,
    load,
    refresh,
    copyJson,
    downloadJson,
    reset,
  }
}
