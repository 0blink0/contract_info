import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { deleteKbEntry, getKbEntries, type KbEntryItem } from '@/api/kb'

const DEBOUNCE_MS = 300

export function useKbConfigList() {
  const loading = ref(false)
  const keyword = ref('')
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const items = ref<KbEntryItem[]>([])

  let timer: ReturnType<typeof setTimeout> | null = null
  let requestSeq = 0

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  async function refresh() {
    loading.value = true
    const seq = ++requestSeq
    try {
      const res = await getKbEntries({
        field_name: keyword.value,
        page: page.value,
        page_size: pageSize.value,
      })
      if (seq !== requestSeq) return
      items.value = res.items ?? []
      total.value = res.total ?? 0
      if (total.value > 0 && page.value > totalPages.value) {
        page.value = totalPages.value
      }
    } catch (e) {
      if (seq !== requestSeq) return
      items.value = []
      total.value = 0
      ElMessage.error(e instanceof Error ? e.message : '知识库列表加载失败')
    } finally {
      if (seq === requestSeq) loading.value = false
    }
  }

  function onPageChange(nextPage: number) {
    page.value = nextPage
    void refresh()
  }

  function onPageSizeChange(nextSize: number) {
    pageSize.value = nextSize
    page.value = 1
    void refresh()
  }

  async function remove(id: string): Promise<boolean> {
    try {
      await deleteKbEntry(id)
      ElMessage.success('已删除知识库条目')
      await refresh()
      return true
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '删除知识库条目失败')
      return false
    }
  }

  watch(
    keyword,
    () => {
      page.value = 1
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        void refresh()
      }, DEBOUNCE_MS)
    },
    { flush: 'post' },
  )

  return {
    loading,
    keyword,
    page,
    pageSize,
    total,
    items,
    refresh,
    onPageChange,
    onPageSizeChange,
    remove,
  }
}
