import { computed, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { JobPreviewSectionResponse } from '@/api/types'
import { getJobPreviewSection, saveJobPreviewSection } from '@/api/client'
import {
  buildSectionSaveBody,
  isValidTableKey,
  normalizeSectionPreview,
  type TableKey,
} from '@/constants/jobSections'
import { useJobDetailInject } from '@/composables/useJobDetailContext'

const PREVIEW_STATUSES = new Set(['extracted', 'exporting', 'exported', 'export_failed'])

export function useSectionPreview(tableKey: Ref<string>) {
  const { jobId, status } = useJobDetailInject()

  const preview = ref<JobPreviewSectionResponse | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const dirty = ref(false)

  const validKey = computed(() =>
    isValidTableKey(tableKey.value) ? (tableKey.value as TableKey) : null,
  )

  const canEdit = computed(
    () =>
      Boolean(
        validKey.value &&
          preview.value &&
          (status.value === 'extracted' ||
            status.value === 'exported' ||
            status.value === 'export_failed'),
      ),
  )

  const canShowPreview = computed(
    () => Boolean(validKey.value && PREVIEW_STATUSES.has(status.value)),
  )

  function markDirty() {
    dirty.value = true
  }

  async function load() {
    const key = validKey.value
    const id = jobId.value
    if (!key || !id || !PREVIEW_STATUSES.has(status.value)) {
      preview.value = null
      dirty.value = false
      return
    }
    loading.value = true
    try {
      const data = await getJobPreviewSection(id, key)
      preview.value = normalizeSectionPreview(key, data)
      dirty.value = false
    } catch (e) {
      preview.value = null
      if (status.value === 'exported' || status.value === 'extracted') {
        ElMessage.warning(e instanceof Error ? e.message : '预览加载失败')
      }
    } finally {
      loading.value = false
    }
  }

  async function save() {
    const key = validKey.value
    const id = jobId.value
    if (!key || !id || !preview.value || !canEdit.value) return
    saving.value = true
    try {
      const body = buildSectionSaveBody(key, preview.value)
      const data = await saveJobPreviewSection(id, key, body)
      preview.value = normalizeSectionPreview(key, data)
      dirty.value = false
      ElMessage.success('已保存并重新生成 Excel，下载将使用最新内容')
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  watch(
    () => [validKey.value, status.value, jobId.value] as const,
    () => void load(),
    { immediate: true },
  )

  return {
    preview,
    loading,
    saving,
    dirty,
    canEdit,
    canShowPreview,
    markDirty,
    load,
    save,
  }
}
