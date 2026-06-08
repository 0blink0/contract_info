import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

import { postKbEntries } from '@/api/kb'
import type { CrmHandoffItem } from '@/api/types'

export interface KbRow {
  field_name: string
  field_value: string
  snippet: string
  selected: boolean
}

const KB_FIELDS = ['业绩报酬提取方式', '业绩基准类型', '门槛净值类型', '提取时点'] as const

export function useKbEntry(
  jobId: Ref<string | null>,
  jobFilename: Ref<string | null>,
  crmRows: Ref<CrmHandoffItem[]>,
) {
  const kbRows = ref<KbRow[]>([])
  const submitting = ref(false)
  const kbUnavailable = ref(false)

  function buildRows() {
    kbRows.value = KB_FIELDS.map((fieldName) => {
      const row = crmRows.value.find((r) => r.crm_field === fieldName)
      return {
        field_name: fieldName,
        field_value: row?.suggested_value ?? '',
        snippet: row?.snippet ?? '',
        selected: false,
      }
    })
  }

  async function submit() {
    const selected = kbRows.value.filter((r) => r.selected)
    if (!selected.length || !jobId.value) {
      return
    }
    submitting.value = true
    try {
      const res = await postKbEntries({
        entries: selected.map((r) => ({
          field_name: r.field_name,
          field_value: r.field_value,
          snippet: r.snippet,
          source_job_id: jobId.value!,
          source_filename: jobFilename.value ?? '',
        })),
      })
      ElMessage.success(`已存入 ${res.count} 条`)
    } catch (e) {
      if (e instanceof Error && e.message.includes('503')) {
        kbUnavailable.value = true
        ElMessage.error('知识库不可用，请检查模型是否已加载')
      } else {
        ElMessage.error(e instanceof Error ? e.message : '存入失败')
      }
    } finally {
      submitting.value = false
    }
  }

  return { kbRows, submitting, kbUnavailable, buildRows, submit }
}
