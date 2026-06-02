<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import LlmConfigForm from '@/components/LlmConfigForm.vue'
import { markConfigReady, resetOnboardingCompletion } from '@/stores/appBootstrap'
import type { AppSettings } from '../../../electron/types/ipc'

const loading = ref(false)
const saving = ref(false)
const formValid = ref(false)
const backendState = ref('idle')
const reconnecting = computed(() => backendState.value === 'restarting' || saving.value)
const SAVE_TIMEOUT_MS = 20_000

const formData = ref<AppSettings>({
  llmBaseUrl: '',
  llmApiKey: '',
  llmModel: '',
  temperature: 0.2,
  ragTopK: 3,
})

let unbindStatus: (() => void) | null = null
let originalApiKey = ''

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | null = null
  try {
    const timeoutPromise = new Promise<T>((_, reject) => {
      timer = setTimeout(() => reject(new Error(message)), timeoutMs)
    })
    return await Promise.race([promise, timeoutPromise])
  } finally {
    if (timer) clearTimeout(timer)
  }
}

onMounted(async () => {
  if (!window.api) return
  loading.value = true
  const result = await window.api.loadSettings()
  loading.value = false
  if (!result.ok) {
    ElMessage.error(result.error?.message ?? '加载配置失败')
    return
  }
  const rawTopK = Number(result.data.ragTopK ?? 3)
  const normalizedTopK = Number.isInteger(rawTopK) && rawTopK >= 1 && rawTopK <= 10 ? rawTopK : 3
  formData.value = {
    ...formData.value,
    ...result.data,
    ragTopK: normalizedTopK,
  }
  originalApiKey = result.data.llmApiKey ?? ''
  unbindStatus = window.api.onBackendStatus((payload) => {
    backendState.value = payload.state
  })
})

onUnmounted(() => {
  if (unbindStatus) unbindStatus()
})

async function saveSettings(): Promise<void> {
  if (!window.api) return
  if (!formValid.value) {
    ElMessage.warning('请先填写完整且合法的配置')
    return
  }
  if (formData.value.llmApiKey !== originalApiKey) {
    await ElMessageBox.confirm(
      '你修改了 API Key，保存后将立即重启后端并应用新配置，是否继续？',
      '确认修改 API Key',
      {
        type: 'warning',
        confirmButtonText: '继续保存',
        cancelButtonText: '取消',
      },
    )
  }
  saving.value = true
  const payload: AppSettings = {
    llmBaseUrl: String(formData.value.llmBaseUrl ?? ''),
    llmApiKey: String(formData.value.llmApiKey ?? ''),
    llmModel: String(formData.value.llmModel ?? ''),
    temperature: Number.isFinite(formData.value.temperature) ? Number(formData.value.temperature) : 0.2,
    ragTopK: (() => {
      const candidate = Number(formData.value.ragTopK ?? 3)
      return Number.isInteger(candidate) && candidate >= 1 && candidate <= 10 ? candidate : 3
    })(),
  }
  let result
  try {
    result = await withTimeout(
      window.api.saveSettings(payload),
      SAVE_TIMEOUT_MS,
      '保存超时，请稍后重试（后端重启超过 20 秒）',
    )
  } catch (error) {
    saving.value = false
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
    return
  }
  saving.value = false
  if (!result.ok) {
    resetOnboardingCompletion()
    ElMessage.error(
      `${result.error?.message ?? '保存失败'}；日志：${result.data.logPath || '未知'}`,
    )
    return
  }
  originalApiKey = formData.value.llmApiKey
  markConfigReady(true)
  ElMessage.success(result.data.rollbackApplied ? '重启失败，已自动回滚旧配置' : '保存成功，后端已重连')
}
</script>

<template>
  <section class="settings-page" v-loading="loading">
    <el-card class="settings-card">
      <template #header>
        <h2>系统设置</h2>
      </template>
      <LlmConfigForm v-model="formData" :disabled="saving" @valid-change="formValid = $event" />
      <el-button type="primary" :loading="saving" :disabled="reconnecting" @click="saveSettings">保存并重启</el-button>
    </el-card>

    <div v-if="reconnecting" class="blocking-mask">
      <el-card>
        <p>正在重连后端，请稍候...</p>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.settings-page {
  position: relative;
  padding: 24px;
}

.settings-card {
  max-width: 860px;
}

.blocking-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  display: grid;
  place-items: center;
  z-index: 999;
}
</style>
