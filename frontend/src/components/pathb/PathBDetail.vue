<script setup lang="ts">
import { computed, onMounted, toRef } from 'vue'
import { usePathB } from '@/composables/usePathB'

const PAGE_UNAVAILABLE = '页码暂未解析'

const props = defineProps<{
  jobId: string
  available: boolean
  autoLoad?: boolean
}>()

const jobIdRef = toRef(props, 'jobId')

const {
  data,
  loading,
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
} = usePathB(jobIdRef)

const showPageNotice = computed(() => true)

onMounted(() => {
  if (props.autoLoad !== false && props.available) {
    void load()
  }
})

defineExpose({ load, refresh })
</script>

<template>
  <div class="path-b-detail">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="字段 B 需 CRM 手录"
      description="业绩报酬与开放日建议摘录供人工判断，不写入 Excel 导入母版。"
      class="top-alert"
    />
    <el-alert
      v-if="showPageNotice"
      type="warning"
      :closable="false"
      show-icon
      title="页码说明"
      description="合同摘录暂未标注页码，请结合下方原文块判断位置。"
      class="page-alert"
    />

    <el-empty v-if="!available" description="暂无路径 B 数据" />

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
          <el-table-column label="页码" width="110">
            <template #default>{{ PAGE_UNAVAILABLE }}</template>
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

        <el-table
          v-if="snippetRows.length"
          :data="snippetRows"
          size="small"
          stripe
          border
          class="section-table"
          empty-text="暂无摘录行"
        >
          <el-table-column prop="label" label="标签" width="140" />
          <el-table-column prop="text" label="摘录" min-width="240" show-overflow-tooltip />
          <el-table-column label="页码" width="110">
            <template #default>{{ PAGE_UNAVAILABLE }}</template>
          </el-table-column>
        </el-table>

        <div v-if="rawSections.length" class="raw-sections">
          <div class="sub-title">合同原文（业绩报酬 / 开放日章节）</div>
          <div v-for="sec in rawSections" :key="sec.key" class="raw-section-block">
            <div class="raw-section-label">{{ sec.label }}</div>
            <pre class="raw-section-text">{{ sec.text }}</pre>
          </div>
        </div>

        <pre v-if="showJson" class="json-block">{{ jsonText }}</pre>
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

.page-alert {
  margin-bottom: 16px;
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

.raw-section-label {
  font-size: 12px;
  font-weight: 600;
  color: #2f5496;
  margin-bottom: 4px;
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
</style>
