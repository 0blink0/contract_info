<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useKbConfigList } from '@/composables/useKbConfigList'
import { useKbStatus } from '@/composables/useKbStatus'
import type { KbEntryItem } from '@/api/kb'

const { loading, keyword, page, pageSize, total, items, refresh, onPageChange, onPageSizeChange, remove } =
  useKbConfigList()

const { modelLoaded } = useKbStatus()  // 共享 AppLayout 的单例轮询，无需重复启动

onMounted(() => {
  void refresh()
})

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

async function onDelete(row: KbEntryItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除字段「${row.field_name}」吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  const ok = await remove(row.id)
  if (!ok) return
}

function copySnippet(snippet: string) {
  if (!snippet) return
  void navigator.clipboard
    .writeText(snippet)
    .then(() => ElMessage.success('已复制原文摘录'))
    .catch(() => ElMessage.error('复制失败'))
}

onMounted(() => {
  void refresh()
})
</script>

<template>
  <div class="page-shell">
    <!-- 向量模型加载状态 -->
    <el-alert
      v-if="modelLoaded === false"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 12px;"
    >
      <template #title>
        <span>向量模型加载中，RAG 功能暂不可用</span>
        <el-icon class="is-loading" style="margin-left: 8px; vertical-align: middle;"><Loading /></el-icon>
      </template>
      <span style="font-size: 12px; color: #666;">首次启动约需 4 分钟，加载完成后此提示自动消失，提取时将自动注入 RAG 增强。</span>
    </el-alert>
    <el-alert
      v-else-if="modelLoaded === true"
      type="success"
      :closable="false"
      show-icon
      title="向量模型已就绪，RAG 功能可用"
      style="margin-bottom: 12px;"
    />

    <div class="list-header">
      <div>
        <h1 class="page-title">知识库配置</h1>
        <p class="page-desc">查看与维护知识库条目，可按字段名筛选并分页浏览。</p>
      </div>
      <div class="toolbar">
        <el-input
          v-model="keyword"
          class="keyword-input"
          clearable
          placeholder="按字段名筛选（即时查询）"
        />
        <el-button :loading="loading" @click="refresh">刷新</el-button>
      </div>
    </div>

    <div class="surface-card">
      <el-table v-loading="loading" :data="items" stripe style="width: 100%" empty-text="暂无知识库条目">
        <el-table-column prop="field_name" label="字段名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="field_value" label="字段值" min-width="220" show-overflow-tooltip />
        <el-table-column label="原文摘录" min-width="260">
          <template #default="{ row }">
            <el-button link type="primary" @click="copySnippet(row.snippet || '')">复制摘录</el-button>
            <span class="snippet">{{ row.snippet || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source_filename" label="来源合同" min-width="180" show-overflow-tooltip />
        <el-table-column label="入库时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-wrap">
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 4px;
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.keyword-input {
  width: 280px;
}

.snippet {
  margin-left: 8px;
  color: #64748b;
}

.pager-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
