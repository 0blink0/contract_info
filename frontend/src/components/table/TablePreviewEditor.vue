<script setup lang="ts">
import { computed } from 'vue'
import type { JobPreviewSectionResponse } from '@/api/types'

import {
  listSectionData,
  listTableEditableColumns,
  productRows,
  sectionKind,
  type TableKey,
} from '@/constants/jobSections'

const props = defineProps<{
  tableKey: TableKey
  preview: JobPreviewSectionResponse | null
  canEdit: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  dirty: []
}>()

const kind = computed(() => sectionKind(props.tableKey))

const productData = computed(() =>
  props.preview ? productRows(props.preview) : [],
)

const listMeta = computed(() => {
  if (!props.preview || kind.value !== 'list') {
    return { columns: [] as string[], rows: [] as Record<string, string | null>[] }
  }
  return listSectionData(props.preview, props.tableKey)
})

const editableCols = computed(() =>
  listTableEditableColumns(listMeta.value.columns, listMeta.value.rows),
)

const emptyText = computed(() => {
  const map: Record<TableKey, string> = {
    'product-elements': '暂无产品要素数据',
    'fee-rates': '暂无费率数据',
    'lock-periods': '暂无锁定期子表数据',
    'share-classes': '暂无分级份额数据',
    'subscription-fee-rates': '暂无申赎费率数据',
  }
  return map[props.tableKey]
})

const confirmedEmptyHint = computed(() => {
  if (!props.preview) return null
  const { rows } = listMeta.value
  if (rows.length > 0) return null
  if (props.tableKey === 'lock-periods' && props.preview.lock_empty_reason === 'confirmed_empty') {
    return 'AI 分析后确认合同未约定份额锁定期（如有实际约定请手动补充）'
  }
  if (props.tableKey === 'share-classes' && props.preview.share_empty_reason === 'confirmed_empty') {
    return 'AI 分析后确认合同未设置分级份额（非分级产品可忽略此项）'
  }
  return null
})

function onInput() {
  emit('dirty')
}
</script>

<template>
  <div class="table-preview-editor">
    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else-if="preview">
      <el-table
        v-if="kind === 'product'"
        :data="productData"
        size="small"
        stripe
        border
        max-height="400"
        :empty-text="emptyText"
      >
        <el-table-column prop="field" label="字段" min-width="160" />
        <el-table-column label="值" min-width="240">
          <template #default="{ row }">
            <el-input
              v-if="canEdit"
              v-model="row.value"
              size="small"
              @input="onInput"
            />
            <span v-else>{{ row.value }}</span>
          </template>
        </el-table-column>
      </el-table>

      <template v-else>
        <el-alert
          v-if="confirmedEmptyHint"
          type="info"
          :closable="false"
          show-icon
          :title="confirmedEmptyHint"
          style="margin-bottom: 8px"
        />
        <el-table
          v-else
          :data="listMeta.rows"
          size="small"
          stripe
          border
          max-height="400"
          :empty-text="emptyText"
        >
        <el-table-column
          v-for="col in editableCols"
          :key="col"
          :label="col"
          min-width="120"
        >
          <template #default="{ row }">
            <el-input
              v-if="canEdit"
              v-model="row[col]"
              size="small"
              @input="onInput"
            />
            <span v-else>{{ row[col] }}</span>
          </template>
        </el-table-column>
        </el-table>
      </template>
    </template>
  </div>
</template>

<style scoped>
.table-preview-editor {
  margin-bottom: 20px;
}

</style>
