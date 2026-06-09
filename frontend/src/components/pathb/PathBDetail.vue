<script setup lang="ts">
import { onMounted, ref, toRef, watch } from 'vue'
import { usePathB } from '@/composables/usePathB'
import { useKbEntry, type KbRow } from '@/composables/useKbEntry'
import DocTextDrawer from '@/components/DocTextDrawer.vue'

const props = defineProps<{
  jobId: string
  available: boolean
  autoLoad?: boolean
}>()

const jobIdRef = toRef(props, 'jobId')
const jobFilenameRef = ref<string | null>(null)

const {
  data,
  loading,
  showJson,
  crmRows,
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
} = usePathB(jobIdRef)

const { kbRows, submitting, kbUnavailable, buildRows, submit } = useKbEntry(
  jobIdRef,
  jobFilenameRef,
  crmRows,
)

watch(
  () => data.value,
  (val) => {
    if (val) buildRows()
  },
  { immediate: true },
)

onMounted(() => {
  if (props.autoLoad !== false && props.available) {
    void load()
  }
})

const drawerOpen = ref(false)
const drawerExcerpt = ref<string | null>(null)

function openDrawer(text: string) {
  drawerExcerpt.value = text
  drawerOpen.value = true
}

defineExpose({ load, refresh })
</script>

<template>
  <div class="path-b-detail">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="开放日与业绩报酬需 CRM 手录"
      description="业绩报酬与开放日建议摘录供人工判断，不写入 Excel 导入母版。"
      class="top-alert"
    />
    <el-empty v-if="!available" description="暂无开放日与业绩报酬数据" />

    <template v-else>
      <div class="actions">
        <el-button size="small" :loading="loading" @click="refresh">刷新</el-button>
        <el-button size="small" :disabled="!data" @click="showJson = !showJson">
          {{ showJson ? '隐藏 JSON' : '查看 JSON' }}
        </el-button>
        <el-button size="small" :disabled="!data" @click="copyJson">复制 JSON</el-button>
        <el-button size="small" :disabled="!data" @click="downloadJson">下载原始 JSON</el-button>
      </div>

      <el-skeleton v-if="loading && !data" :rows="4" animated />

      <template v-else-if="data">
        <el-alert
          v-for="w in (data.rag_warnings ?? [])"
          :key="w.code"
          :type="w.code === 'rag_injected' ? 'success' : w.code === 'rag_model_loading' ? 'warning' : 'error'"
          :title="w.message"
          :closable="false"
          show-icon
          class="rag-alert"
        />

        <p v-if="data.open_day?.fixed_schedule" class="field-line">
          <strong>固定开放日：</strong>{{ data.open_day.fixed_schedule }}
        </p>
        <p class="summary-line">
          CRM 业绩报酬设置：已建议
          <strong>{{ filledCount }}</strong>
          / 6 项（对照图二「业绩报酬提取设置」手录）
        </p>

        <el-table
          v-if="tierRows.length"
          :data="tierRows"
          size="small"
          stripe
          border
          class="section-table"
          empty-text="无业绩报酬档位"
        >
          <el-table-column prop="share_class" label="份额" width="80" />
          <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
          <el-table-column prop="ratio_pct" label="比例%" width="90" />
        </el-table>

        <el-table
          :data="crmRows"
          size="small"
          stripe
          border
          class="section-table"
          empty-text="暂无 CRM 字段建议"
        >
          <el-table-column prop="crm_field" label="CRM 字段" width="150" />
          <el-table-column label="建议填写" min-width="160">
            <template #default="{ row }">
              <span v-if="row.suggested_value">{{ row.suggested_value }}</span>
              <el-text v-else type="info">— 未从合同推断 —</el-text>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="coverageTagType(row.coverage)" size="small">
                {{ coverageLabel(row.coverage) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="diagnostic" label="诊断说明" min-width="160" show-overflow-tooltip />
          <el-table-column prop="snippet" label="合同摘录" min-width="220" show-overflow-tooltip />
        </el-table>

        <div v-if="rawSections.length" class="raw-sections">
          <div class="sub-title">合同原文（业绩报酬 / 开放日章节）</div>
          <div v-for="sec in rawSections" :key="sec.key" class="raw-section-block">
            <div class="raw-section-header">
              <div class="raw-section-label">{{ sec.label }}</div>
              <el-button size="small" link type="primary" @click="openDrawer(sec.text)">
                查看原文位置
              </el-button>
            </div>
            <pre class="raw-section-text">{{ sec.text }}</pre>
          </div>
        </div>

        <pre v-if="showJson" class="json-block">{{ jsonText }}</pre>

        <DocTextDrawer
          v-model="drawerOpen"
          :job-id="jobId"
          :excerpt="drawerExcerpt"
        />

        <div v-if="available" class="kb-entry-section">
          <div class="sub-title">存入知识库</div>

          <el-alert
            v-if="kbUnavailable"
            type="warning"
            :closable="false"
            title="知识库功能不可用（模型未加载）"
            class="kb-alert"
          />

          <el-table
            :data="kbRows"
            size="small"
            stripe
            border
            class="section-table"
            @selection-change="(sel: KbRow[]) => kbRows.forEach((r) => { r.selected = sel.includes(r) })"
          >
            <el-table-column type="selection" width="46" />
            <el-table-column prop="field_name" label="字段名" width="150" />
            <el-table-column label="字段值" min-width="160">
              <template #default="{ row }">
                <el-input
                  v-model="row.field_value"
                  size="small"
                  :disabled="kbUnavailable"
                  placeholder="（可修改）"
                />
              </template>
            </el-table-column>
            <el-table-column label="原文摘录" min-width="240">
              <template #default="{ row }">
                <el-input
                  v-model="row.snippet"
                  size="small"
                  type="textarea"
                  :autosize="{ minRows: 1, maxRows: 3 }"
                  :disabled="kbUnavailable"
                  placeholder="（可选）"
                />
              </template>
            </el-table-column>
          </el-table>

          <el-button
            type="primary"
            size="small"
            :loading="submitting"
            :disabled="kbUnavailable || !kbRows.some((r: KbRow) => r.selected)"
            @click="submit"
          >
            存入知识库
          </el-button>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.path-b-detail {
  width: 100%;
}

.top-alert {
  margin-bottom: 12px;
}

.actions {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.section-table {
  margin-bottom: 12px;
}

.field-line {
  margin: 0 0 8px;
  font-size: 13px;
}

.summary-line {
  margin: 0 0 10px;
  font-size: 13px;
  color: #606266;
}

.raw-sections {
  margin-bottom: 12px;
}

.raw-section-block {
  margin-bottom: 16px;
}

.raw-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.raw-section-label {
  font-size: 12px;
  font-weight: 600;
  color: #2f5496;
  padding: 2px 6px;
  background: #deebf7;
  border-radius: 3px;
  display: inline-block;
}

.raw-section-text {
  margin: 0;
  padding: 10px 12px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.7;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 320px;
  overflow-y: auto;
}

.sub-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.json-block {
  margin-top: 12px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.kb-entry-section {
  margin-top: 16px;
}

.kb-alert {
  margin-bottom: 8px;
}

.rag-alert {
  margin-bottom: 8px;
}
</style>
