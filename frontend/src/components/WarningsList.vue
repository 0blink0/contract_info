<script setup lang="ts">
import type { WarningItem } from '@/api/types'

defineProps<{
  warnings: WarningItem[]
  count: number
}>()
</script>

<template>
  <div v-if="count > 0" class="warnings">
    <el-collapse>
      <el-collapse-item :title="`校验提示（${count} 条）`" name="warnings">
        <el-table :data="warnings" size="small" stripe>
          <el-table-column prop="field" label="字段" width="140" />
          <el-table-column prop="code" label="代码" width="120" />
          <el-table-column prop="message" label="说明" min-width="200" />
          <el-table-column prop="suggestion" label="建议" min-width="160" />
        </el-table>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>
