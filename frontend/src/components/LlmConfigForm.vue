<script setup lang="ts">
import { computed, watch } from 'vue'
import type { AppSettings } from '../../../electron/types/ipc'

const props = defineProps<{
  modelValue: AppSettings
  disabled?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: AppSettings): void
  (event: 'valid-change', value: boolean): void
}>()

const form = computed({
  get: () => props.modelValue,
  set: (value: AppSettings) => emit('update:modelValue', value),
})

const valid = computed(() => {
  const base = form.value.llmBaseUrl?.trim()
  const key = form.value.llmApiKey?.trim()
  const model = form.value.llmModel?.trim()
  const ragTopK = Number(form.value.ragTopK ?? 3)
  if (!base || !key || !model) return false
  if (!Number.isInteger(ragTopK) || ragTopK < 1 || ragTopK > 10) return false
  try {
    // eslint-disable-next-line no-new
    new URL(base)
    return true
  } catch {
    return false
  }
})

watch(valid, (value) => emit('valid-change', value), { immediate: true })
</script>

<template>
  <el-form label-position="top" class="llm-config-form">
    <el-form-item label="LLM Base URL" required>
      <el-input v-model="form.llmBaseUrl" :disabled="disabled" placeholder="https://api.openai.com/v1" />
    </el-form-item>
    <el-form-item label="LLM API Key" required>
      <el-input
        v-model="form.llmApiKey"
        :disabled="disabled"
        show-password
        placeholder="sk-..."
      />
    </el-form-item>
    <el-form-item label="LLM Model" required>
      <el-input v-model="form.llmModel" :disabled="disabled" placeholder="gpt-4o-mini" />
    </el-form-item>
    <el-form-item label="Temperature">
      <el-input-number v-model="form.temperature" :disabled="disabled" :min="0" :max="2" :step="0.1" />
    </el-form-item>
    <el-form-item label="RAG Top-K">
      <el-input-number v-model="form.ragTopK" :disabled="disabled" :min="1" :max="10" :step="1" />
    </el-form-item>
  </el-form>
</template>

<style scoped>
.llm-config-form {
  max-width: 640px;
}
</style>
