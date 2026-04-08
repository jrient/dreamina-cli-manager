<!-- frontend/src/views/ProjectTasks.vue -->
<template>
  <div class="project-tasks">
    <div class="page-header">
      <el-button text @click="$router.push('/projects')">
        <el-icon><ArrowLeft /></el-icon>
        返回项目列表
      </el-button>
      <h2>{{ project?.name || '...' }} - 任务</h2>
      <el-button type="primary" @click="$router.push(`/projects/${projectId}/materials`)">
        <el-icon><FolderOpened /></el-icon>
        素材
      </el-button>
    </div>

    <SubmitTask :project-id="projectId" @submitted="loadTasks" />

    <el-divider />

    <div class="task-list-header">
      <h3>任务列表</h3>
      <el-button @click="loadTasks">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <el-table :data="tasks" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="120" />
      <el-table-column prop="label" label="标签" width="150">
        <template #default="{ row }">
          <span v-if="row.label">{{ row.label }}</span>
          <span v-else style="color: #909399">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button text type="primary" @click="copyTask(row)">
            <el-icon><CopyDocument /></el-icon>
          </el-button>
          <el-button text type="danger" @click="confirmDelete(row)">
            <el-icon><Delete /></el-icon>
          </el-button>
          <el-button v-if="row.result_url" text type="success" @click="openResult(row)">
            <el-icon><VideoPlay /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, FolderOpened, Refresh, CopyDocument, Delete, VideoPlay } from '@element-plus/icons-vue'
import { api } from '../api/index.js'
import SubmitTask from './SubmitTask.vue'

const route = useRoute()
const projectId = computed(() => route.params.id)

const project = ref(null)
const tasks = ref([])
const loading = ref(false)

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const getStatusType = (status) => {
  const types = { pending: 'warning', running: 'primary', success: 'success', failed: 'danger', queued: 'info' }
  return types[status] || 'info'
}

const loadProject = async () => {
  try {
    project.value = await api.getProject(projectId.value)
  } catch (e) {
    ElMessage.error('加载项目失败: ' + e.message)
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    tasks.value = await api.listTasks({ project_id: projectId.value })
  } catch (e) {
    ElMessage.error('加载任务失败: ' + e.message)
  }
  loading.value = false
}

const copyTask = async (task) => {
  try {
    const newTask = await api.copyTask(task.id)
    ElMessage.success('任务复制成功: ' + newTask.id)
    loadTasks()
  } catch (e) {
    ElMessage.error('复制失败: ' + e.message)
  }
}

const confirmDelete = (task) => {
  ElMessageBox.confirm(`确定删除任务 ${task.id}?`, '删除任务', { type: 'warning' })
    .then(async () => {
      try {
        await api.deleteTask(task.id)
        ElMessage.success('任务已删除')
        loadTasks()
      } catch (e) {
        ElMessage.error('删除失败: ' + e.message)
      }
    }).catch(() => {})
}

const openResult = (task) => {
  if (task.result_url) {
    window.open(task.result_url, '_blank')
  }
}

onMounted(() => {
  loadProject()
  loadTasks()
})
</script>

<style scoped>
.project-tasks {
  padding: 20px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.page-header h2 {
  margin: 0;
}
.task-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.task-list-header h3 {
  margin: 0;
}
</style>