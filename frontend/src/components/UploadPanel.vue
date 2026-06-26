<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { upload } from '@/api/client'

const emit = defineEmits<{
  uploaded: [jobId: string]
}>()

const uploading = ref(false)

async function onFileChange(file: { raw?: File }) {
  const raw = file.raw
  if (!raw) return
  const name = raw.name.toLowerCase()
  if (!name.endsWith('.docx') && !name.endsWith('.pdf')) {
    ElMessage.error('仅支持 .docx / .pdf 文件')
    return
  }
  uploading.value = true
  try {
    const res = await upload(raw)
    ElMessage.success('上传成功')
    emit('uploaded', res.job_id)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="upload-panel">
    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="false"
      accept=".docx,.pdf"
      :disabled="uploading"
      @change="onFileChange"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽或点击上传合同 <em>.docx / .pdf</em></div>
    </el-upload>
  </div>
</template>

<style scoped>
.upload-panel {
  margin-top: 12px;
}
</style>
