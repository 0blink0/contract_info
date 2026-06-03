<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import LlmConfigForm from '@/components/LlmConfigForm.vue'
import {
  completeOnboarding,
  setOnboardingStep,
  updateOnboardingDraft,
  useAppBootstrapStore,
} from '@/stores/appBootstrap'
import type { AppSettings } from '../../../electron/types/ipc'

const steps = ['欢迎', '配置凭证', '连接测试']
const router = useRouter()
const { state } = useAppBootstrapStore()

const currentStep = ref(state.onboardingStep)
const formData = ref<AppSettings>({ ...state.onboardingDraft })
const formValid = ref(false)
const testing = ref(false)
const testPassed = ref(false)
const finishing = ref(false)
const SAVE_TIMEOUT_MS = 20_000

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

function nextStep(): void {
  if (currentStep.value === 1 && !formValid.value) {
    ElMessage.warning('请先完成有效配置')
    return
  }
  if (currentStep.value < 2) {
    currentStep.value += 1
    setOnboardingStep(currentStep.value)
  }
}

function prevStep(): void {
  if (currentStep.value > 0) {
    currentStep.value -= 1
    setOnboardingStep(currentStep.value)
  }
}

async function runConnectionTest(): Promise<void> {
  testing.value = true
  testPassed.value = false
  updateOnboardingDraft(formData.value)
  try {
    const rawBase = formData.value.llmBaseUrl.trim().replace(/\/+$/, '')
    const candidates = [`${rawBase}/models`, `${rawBase}/v1/models`]
    let connected = false
    let lastStatus = 0

    for (const target of candidates) {
      try {
        const response = await fetch(target, {
          headers: {
            Authorization: `Bearer ${formData.value.llmApiKey}`,
          },
        })
        lastStatus = response.status
        if (response.ok) {
          connected = true
          break
        }
        if (response.status !== 404) break
      } catch {
        // try next candidate
      }
    }

    if (!connected) {
      throw new Error(`LLM connection test failed: ${lastStatus || 'network_error'}`)
    }
    testPassed.value = true
    ElMessage.success('连接测试通过')
  } catch (error) {
    testPassed.value = false
    ElMessage.error(error instanceof Error ? error.message : '连接测试失败')
  } finally {
    testing.value = false
  }
}

async function finishWizard(): Promise<void> {
  if (!testPassed.value) {
    ElMessage.warning('请先通过连接测试')
    return
  }
  if (!window.api) {
    ElMessage.error('桌面 API 不可用')
    return
  }
  finishing.value = true
  const payload: AppSettings = {
    llmBaseUrl: String(formData.value.llmBaseUrl ?? ''),
    llmApiKey: String(formData.value.llmApiKey ?? ''),
    llmModel: String(formData.value.llmModel ?? ''),
    temperature: Number.isFinite(formData.value.temperature) ? Number(formData.value.temperature) : 0.2,
    ragTopK: Number.isInteger(formData.value.ragTopK) ? (formData.value.ragTopK as number) : 3,
  }
  let result
  try {
    result = await withTimeout(
      window.api.saveSettings(payload),
      SAVE_TIMEOUT_MS,
      '保存超时，请稍后重试（后端重启超过 20 秒）',
    )
  } catch (error) {
    finishing.value = false
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
    return
  }
  finishing.value = false
  if (!result.ok) {
    ElMessage.error(result.error?.message ?? '保存配置失败')
    return
  }
  completeOnboarding(formData.value)
  ElMessage.success('配置已生效，正在进入主界面')
  void router.replace('/upload')
}

const canFinish = computed(() => testPassed.value && !testing.value && !finishing.value)
</script>

<template>
  <section class="wizard-page">
    <el-card class="wizard-card">
      <template #header>
        <div class="wizard-header">
          <h2>首次启动向导</h2>
          <el-steps :active="currentStep" finish-status="success" simple>
            <el-step v-for="item in steps" :key="item" :title="item" />
          </el-steps>
        </div>
      </template>

      <div v-if="currentStep === 0" class="wizard-content">
        <h3>欢迎使用合同要素抽取桌面版</h3>
        <p>完成 3 步初始化后才可进入主界面。</p>
      </div>

      <div v-else-if="currentStep === 1" class="wizard-content">
        <LlmConfigForm
          v-model="formData"
          @valid-change="formValid = $event"
          @update:model-value="updateOnboardingDraft($event)"
        />
      </div>

      <div v-else class="wizard-content">
        <p>请先进行连接测试，未通过前无法完成向导。</p>
        <el-button :loading="testing" type="primary" @click="runConnectionTest">开始测试</el-button>
        <el-tag v-if="testPassed" type="success" class="test-ok">测试通过</el-tag>
      </div>

      <div class="wizard-actions">
        <el-button :disabled="currentStep === 0 || finishing" @click="prevStep">上一步</el-button>
        <el-button v-if="currentStep < 2" type="primary" :disabled="finishing" @click="nextStep">下一步</el-button>
        <el-button v-else type="success" :disabled="!canFinish" :loading="finishing" @click="finishWizard">
          完成并进入系统
        </el-button>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.wizard-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.wizard-card {
  width: min(900px, 100%);
}

.wizard-header {
  display: grid;
  gap: 12px;
}

.wizard-content {
  margin: 20px 0;
}

.wizard-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.test-ok {
  margin-left: 12px;
}
</style>
