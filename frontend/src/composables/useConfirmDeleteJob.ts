import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteJob } from '@/api/client'

export async function confirmAndDeleteJob(
  jobId: string,
  filename: string,
): Promise<boolean> {
  try {
    await ElMessageBox.confirm(
      `确定删除「${filename}」？将同时删除上传文件、导出 Excel 及数据库记录。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return false
  }
  try {
    await deleteJob(jobId)
    ElMessage.success('已删除')
    return true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
    return false
  }
}
