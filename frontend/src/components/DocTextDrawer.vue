<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getDocumentText } from '@/api/client'
import type { DocumentParagraph } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
  jobId: string
  /** 当前选中字段的原文摘录，用于定位高亮 */
  excerpt: string | null
  /**
   * 字段值（可选）。用于在摘录未命中的表格中做二次扫描：
   * 找到包含该值的单元格并用橙色高亮，弥补摘录来自不同章节时的定位盲区。
   * 长度 < 4 时不启用（避免 "1" 这类短值误匹配）。
   */
  fieldValue?: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
}>()

const paragraphs = ref<DocumentParagraph[]>([])
const loading = ref(false)
const loaded = ref<string | null>(null)

// ─── 匹配导航 ───────────────────────────────────────────────
const currentMatchPos = ref(0)

function excerptChunks(excerpt: string | null): string[] {
  if (!excerpt?.trim()) return []
  const sentences = excerpt
    .split(/[。！？；\n]+/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 6)
  if (sentences.length) return sentences
  const fallback = excerpt.trim().slice(0, 20)
  return fallback.length >= 4 ? [fallback] : []
}

/**
 * 归一化：将 " | " 管道符与 \t 制表符统一成单空格。
 * 后端给 LLM 的源文用 \t 分隔表格列，全文 API 用 " | " 分隔，
 * 两者都归一化才能跨来源匹配。
 */
function normForMatch(s: string): string {
  return s
    .replace(/\s*[|｜]\s*/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const matchData = computed((): { indices: Set<number>; chunks: string[] } => {
  const chunks = excerptChunks(props.excerpt)
  if (!chunks.length) return { indices: new Set(), chunks: [] }
  const normChunks = chunks.map(normForMatch)
  const normExcerpt = normForMatch(props.excerpt ?? '')

  const indices = new Set<number>()
  paragraphs.value.forEach((p, i) => {
    const normText = normForMatch(p.text)
    // 正向检查：段落/表格全文包含 excerpt chunk
    if (normChunks.some((c) => normText.includes(c))) {
      indices.add(i)
      return
    }
    // 反向检查（仅表格 block）：excerpt 包含某个 cell 文本（>=4字）。
    // 场景：摘录来自费用章节的公式段，提到"认购费率"、"年管理费率"等标签词，
    // 而费率分类表的行标签 cell 正是这些词，正向检查因 chunk 比 cell 长而失败。
    if (p.type === 'table' && p.rows?.length && normExcerpt) {
      const hit = p.rows.some((row) =>
        row.some((cell) => {
          const nc = normForMatch(cell)
          return nc.length >= 4 && normExcerpt.includes(nc)
        }),
      )
      if (hit) indices.add(i)
    }
  })

  if (!indices.size) {
    const fallback = normForMatch(props.excerpt?.trim().slice(0, 15) ?? '')
    if (fallback.length >= 4) {
      paragraphs.value.forEach((p, i) => {
        if (normForMatch(p.text).includes(fallback)) indices.add(i)
      })
      return { indices, chunks: fallback.length ? [fallback] : chunks }
    }
  }
  return { indices, chunks }
})

const matchIndices = computed(() => matchData.value.indices)

/** 匹配段落的有序列表，用于导航 */
const matchList = computed(() => [...matchIndices.value])

const totalMatches = computed(() => matchList.value.length)

function scrollToMatch(pos: number) {
  const list = matchList.value
  if (!list.length) return
  const clamped = Math.max(0, Math.min(pos, list.length - 1))
  currentMatchPos.value = clamped
  nextTick(() => {
    const el = paragraphRefs.value[list[clamped]]
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

function prevMatch() { scrollToMatch(currentMatchPos.value - 1) }
function nextMatch() { scrollToMatch(currentMatchPos.value + 1) }

// excerpt/jobId 变化时重置到第一处
watch(() => props.excerpt, () => {
  currentMatchPos.value = 0
  if (props.modelValue) scrollToMatch(0)
})

// ─── fieldValue 二次扫描 ──────────────────────────────────────
/** 字段值是否足够长，可以安全地做二次扫描 */
const canScanValue = computed(() => {
  const v = normForMatch(props.fieldValue ?? '')
  return v.length >= 4
})

/**
 * 基于字段值做表格 block 的二次匹配：
 * 表格 para.text 的归一化文本包含归一化字段值 → 该 block 列为"值命中"。
 */
const valueMatchIndices = computed((): Set<number> => {
  if (!canScanValue.value) return new Set()
  const normVal = normForMatch(props.fieldValue!)
  const result = new Set<number>()
  paragraphs.value.forEach((p, i) => {
    // 只扫表格块；摘录已命中的不重复标记
    if (p.type !== 'table' || matchIndices.value.has(i)) return
    if (normForMatch(p.text).includes(normVal)) result.add(i)
  })
  return result
})

/** 表格单元格是否被字段值命中 */
function cellValueMatched(cell: string): boolean {
  if (!canScanValue.value) return false
  const normCell = normForMatch(cell)
  if (normCell.length < 2) return false
  return normCell.includes(normForMatch(props.fieldValue!))
}

// ─── 文本高亮 ─────────────────────────────────────────────────
/** 将文本按匹配子句拆分成高亮分段 */
function splitHighlight(text: string): Array<{ t: string; hi: boolean }> {
  const chunks = matchData.value.chunks
  if (!chunks.length) return [{ t: text, hi: false }]
  const intervals: Array<[number, number]> = []
  for (const chunk of chunks) {
    let start = 0
    while (start < text.length) {
      const idx = text.indexOf(chunk, start)
      if (idx === -1) break
      intervals.push([idx, idx + chunk.length])
      start = idx + chunk.length
    }
  }
  if (!intervals.length) return [{ t: text, hi: false }]
  return mergeIntervals(text, intervals)
}

/**
 * 表格单元格专用细粒度 chunks（额外按 | 拆分）。
 * 摘录粗 chunks 是整行，比单个 cell 长；细粒度拆开才能在 cell 内定位。
 */
function cellLevelChunks(excerpt: string | null): string[] {
  if (!excerpt?.trim()) return []
  return excerpt
    .split(/[。！？；\n]+|\s*[|｜]\s*/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 4)
}

/** 判断某个表格单元格文本是否命中摘录 */
function cellMatched(cell: string): boolean {
  const normCell = normForMatch(cell)
  if (normCell.length < 2) return false
  if (props.excerpt && normForMatch(props.excerpt).includes(normCell)) return true
  return cellLevelChunks(props.excerpt).some((c) => normCell.includes(normForMatch(c)))
}

/** 表格单元格专用高亮拆分（用细粒度 chunks） */
function splitHighlightCell(text: string): Array<{ t: string; hi: boolean }> {
  const chunks = cellLevelChunks(props.excerpt)
  if (!chunks.length) return [{ t: text, hi: false }]
  const intervals: Array<[number, number]> = []
  for (const chunk of chunks) {
    let start = 0
    while (start < text.length) {
      const idx = text.indexOf(chunk, start)
      if (idx === -1) break
      intervals.push([idx, idx + chunk.length])
      start = idx + chunk.length
    }
  }
  if (!intervals.length) return [{ t: text, hi: false }]
  return mergeIntervals(text, intervals)
}

function mergeIntervals(text: string, intervals: Array<[number, number]>): Array<{ t: string; hi: boolean }> {
  intervals.sort((a, b) => a[0] - b[0])
  const merged: Array<[number, number]> = [intervals[0]]
  for (let i = 1; i < intervals.length; i++) {
    const last = merged[merged.length - 1]
    if (intervals[i][0] <= last[1]) {
      last[1] = Math.max(last[1], intervals[i][1])
    } else {
      merged.push(intervals[i])
    }
  }
  const parts: Array<{ t: string; hi: boolean }> = []
  let cursor = 0
  for (const [s, e] of merged) {
    if (s > cursor) parts.push({ t: text.slice(cursor, s), hi: false })
    parts.push({ t: text.slice(s, e), hi: true })
    cursor = e
  }
  if (cursor < text.length) parts.push({ t: text.slice(cursor), hi: false })
  return parts
}

// ─── 加载 & refs ──────────────────────────────────────────────
const paragraphRefs = ref<HTMLElement[]>([])

function setParagraphRef(el: Element | null, i: number) {
  if (el instanceof HTMLElement) {
    paragraphRefs.value[i] = el
  }
}

async function load() {
  if (!props.jobId || loaded.value === props.jobId) return
  loading.value = true
  try {
    const res = await getDocumentText(props.jobId)
    paragraphs.value = res.paragraphs
    loaded.value = props.jobId
  } catch (e) {
    ElMessage.warning(e instanceof Error ? e.message : '合同全文加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    await load()
    scrollToMatch(0)
  },
)

watch(
  () => props.jobId,
  () => {
    loaded.value = null
    paragraphs.value = []
    paragraphRefs.value = []
    currentMatchPos.value = 0
  },
)

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    title="合同全文"
    direction="rtl"
    size="48%"
    :before-close="close"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-title">合同全文</span>
        <span v-if="!loading && paragraphs.length" class="drawer-meta">
          共 {{ paragraphs.length }} 段
        </span>

        <!-- 摘录命中导航 -->
        <span v-if="totalMatches > 0" class="drawer-match-hint">
          · 已定位
          <template v-if="totalMatches > 1">
            <button class="nav-btn" :disabled="currentMatchPos === 0" @click="prevMatch">‹</button>
            <span class="nav-pos">{{ currentMatchPos + 1 }}/{{ totalMatches }}</span>
            <button class="nav-btn" :disabled="currentMatchPos === totalMatches - 1" @click="nextMatch">›</button>
          </template>
          <template v-else>1</template>
          处匹配
        </span>

        <!-- 字段值二次命中提示 -->
        <span v-if="canScanValue && valueMatchIndices.size > 0" class="drawer-value-hint">
          · 另有 {{ valueMatchIndices.size }} 处含"{{ fieldValue }}"
        </span>
      </div>
    </template>

    <el-skeleton v-if="loading" :rows="8" animated class="drawer-skeleton" />

    <el-empty
      v-else-if="!paragraphs.length"
      description="暂无解析文本（合同尚未完成解析）"
      :image-size="64"
    />

    <div v-else class="doc-body">
      <div
        v-for="(para, i) in paragraphs"
        :key="para.index"
        :ref="(el) => setParagraphRef(el as Element | null, i)"
        class="doc-block"
        :class="{
          'doc-block--matched': matchIndices.has(i),
          'doc-block--value-matched': valueMatchIndices.has(i),
          'doc-block--table': para.type === 'table',
        }"
      >
        <span v-if="para.type === 'table'" class="block-type-badge">表</span>

        <!-- 表格：用 HTML table 渲染，逐单元格高亮 -->
        <div v-if="para.type === 'table' && para.rows?.length" class="doc-table-wrap">
          <table class="doc-table">
            <tbody>
              <tr v-for="(row, ri) in para.rows" :key="ri">
                <td
                  v-for="(cell, ci) in row"
                  :key="ci"
                  class="doc-td"
                  :class="{
                    'doc-td--matched': matchIndices.has(i) && cellMatched(cell),
                    'doc-td--value': valueMatchIndices.has(i) && cellValueMatched(cell),
                  }"
                >
                  <template v-if="matchIndices.has(i)">
                    <template v-for="(seg, si) in splitHighlightCell(cell)" :key="si">
                      <mark v-if="seg.hi" class="excerpt-mark">{{ seg.t }}</mark>
                      <template v-else>{{ seg.t }}</template>
                    </template>
                  </template>
                  <template v-else>{{ cell }}</template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 普通段落（或无 rows 的旧数据回退） -->
        <p v-else class="doc-para">
          <template v-for="(seg, si) in splitHighlight(para.text)" :key="si">
            <mark v-if="seg.hi" class="excerpt-mark">{{ seg.t }}</mark>
            <template v-else>{{ seg.t }}</template>
          </template>
        </p>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.drawer-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.drawer-meta {
  font-size: 12px;
  color: #94a3b8;
}

.drawer-match-hint {
  font-size: 12px;
  color: #2563eb;
  display: flex;
  align-items: center;
  gap: 3px;
}

.drawer-value-hint {
  font-size: 12px;
  color: #d97706;
}

.nav-btn {
  background: none;
  border: 1px solid #93c5fd;
  border-radius: 3px;
  color: #2563eb;
  font-size: 13px;
  line-height: 1;
  padding: 1px 5px;
  cursor: pointer;
  transition: background 0.1s;
}
.nav-btn:hover:not(:disabled) { background: #dbeafe; }
.nav-btn:disabled { opacity: 0.35; cursor: default; }

.nav-pos {
  font-size: 12px;
  color: #1d4ed8;
  min-width: 26px;
  text-align: center;
}

.drawer-skeleton {
  padding: 16px;
}

.doc-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}

.doc-block {
  padding: 8px 12px;
  border-radius: 6px;
  transition: background 0.15s;
}

/* 摘录命中：蓝色左边框 */
.doc-block--matched {
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  padding-left: 9px;
}

/* 字段值命中（摘录未命中）：橙色左边框 */
.doc-block--value-matched {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding-left: 9px;
}

.doc-block--table {
  background: #f8fafc;
}
.doc-block--table.doc-block--matched { background: #eff6ff; }
.doc-block--table.doc-block--value-matched { background: #fffbeb; }

.block-type-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  background: #e2e8f0;
  border-radius: 3px;
  padding: 1px 4px;
  margin-bottom: 4px;
  vertical-align: middle;
}

.doc-para {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: #334155;
  word-break: break-word;
  white-space: pre-wrap;
}

/* 表格渲染 */
.doc-table-wrap {
  overflow-x: auto;
  margin-top: 2px;
}

.doc-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
  color: #334155;
}

.doc-td {
  border: 1px solid #cbd5e1;
  padding: 5px 8px;
  vertical-align: top;
  line-height: 1.6;
  word-break: break-word;
  min-width: 48px;
}

/* 摘录命中单元格：蓝底 */
.doc-td--matched {
  background: #dbeafe;
}

/* 字段值命中单元格：橙底 */
.doc-td--value {
  background: #fef3c7;
  outline: 1px solid #f59e0b;
  outline-offset: -1px;
}

/* 摘录高亮文字 */
.excerpt-mark {
  background: #fde68a;
  color: #78350f;
  border-radius: 2px;
  padding: 0 1px;
  font-style: normal;
}
</style>
