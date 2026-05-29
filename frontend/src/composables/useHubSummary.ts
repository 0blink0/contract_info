import { computed, ref, watch } from 'vue'
import { getJobPreviewSection, getPathB } from '@/api/client'
import {
  JOB_TABLE_SECTIONS,
  normalizeSectionPreview,
  sectionRowCount,
  type TableKey,
} from '@/constants/jobSections'
import { useJobDetailInject } from '@/composables/useJobDetailContext'

const PREVIEW_PLUS = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

export interface TableSummary {
  key: TableKey
  label: string
  rowCount: number | null
  loading: boolean
}

export function useHubSummary() {
  const { jobId, status, detail } = useJobDetailInject()

  const tablesLoading = ref(false)
  const tableSummaries = ref<TableSummary[]>(
    JOB_TABLE_SECTIONS.map((s) => ({
      key: s.key,
      label: s.label,
      rowCount: null,
      loading: false,
    })),
  )

  const pathBSummary = ref<string | null>(null)
  const pathBLoading = ref(false)

  const canLoadSummaries = computed(() => PREVIEW_PLUS.has(status.value))

  async function loadTables() {
    const id = jobId.value
    if (!id || !canLoadSummaries.value) {
      tableSummaries.value = JOB_TABLE_SECTIONS.map((s) => ({
        key: s.key,
        label: s.label,
        rowCount: null,
        loading: false,
      }))
      return
    }
    tablesLoading.value = true
    tableSummaries.value = JOB_TABLE_SECTIONS.map((s) => ({
      key: s.key,
      label: s.label,
      rowCount: null,
      loading: true,
    }))
    try {
      const results = await Promise.all(
        JOB_TABLE_SECTIONS.map(async (s) => {
          const data = await getJobPreviewSection(id, s.key)
          const normalized = normalizeSectionPreview(s.key, data)
          return {
            key: s.key,
            label: s.label,
            rowCount: sectionRowCount(s.key, normalized),
            loading: false,
          }
        }),
      )
      tableSummaries.value = results
    } catch {
      tableSummaries.value = JOB_TABLE_SECTIONS.map((s) => ({
        key: s.key,
        label: s.label,
        rowCount: null,
        loading: false,
      }))
    } finally {
      tablesLoading.value = false
    }
  }

  async function loadPathBSummary() {
    pathBSummary.value = null
    if (!detail.value?.path_b_available || !jobId.value) return
    pathBLoading.value = true
    try {
      const data = await getPathB(jobId.value)
      const filled = (data.crm_handoff ?? []).filter(
        (r) => r.suggested_value && r.coverage !== 'missing',
      ).length
      const openDay = data.open_day?.fixed_schedule
      if (openDay && typeof openDay === 'string') {
        pathBSummary.value = `固定开放日：${openDay}`
      } else {
        pathBSummary.value = `CRM 已建议 ${filled} / 6 项`
      }
    } catch {
      pathBSummary.value = '路径 B 摘要加载失败'
    } finally {
      pathBLoading.value = false
    }
  }

  async function reload() {
    await Promise.all([loadTables(), loadPathBSummary()])
  }

  watch(
    () => [jobId.value, status.value, detail.value?.path_b_available] as const,
    () => void reload(),
    { immediate: true },
  )

  return {
    tableSummaries,
    tablesLoading,
    pathBSummary,
    pathBLoading,
    canLoadSummaries,
    reload,
  }
}
