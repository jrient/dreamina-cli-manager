<!-- frontend/src/views/AdminTasks.vue -->
<template>
  <div class="admin-tasks">
    <div class="page-header">
      <el-button text @click="$router.push('/admin')">
        <el-icon><ArrowLeft /></el-icon>
        返回 Admin
      </el-button>
      <h2>全局任务列表</h2>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterProject" placeholder="按项目筛选" clearable>
        <el-option label="全部" value="" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="按状态筛选" clearable>
        <el-option label="全部" value="" />
        <el-option label="pending" value="pending" />
        <el-option label="running" value="running" />
        <el-option label="success" value="success" />
        <el-option label="failed" value="failed" />
        <el-option label="queued" value="queued" />
      </el-select>
      <el-button @click="loadTasks">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <el-table :data="tasks" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="120" />
      <el-table-column prop="project_id" label="项目" width="150">
        <template #default="{ row }">
          <span v-if="row.project_id">{{ getProjectName(row.project_id) }}</span>
          <span v-else style="color: #909399">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="label" label="标签" width="150">
        <template #default="{ row }">
          <span v-if="row.label">{{ row.label }}</span>
          <span v-else style="color: #909399">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="account_id" label="账号" width="150" />
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
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'failed'"
            text
            type="warning"
            title="重试"
            @click="retryTask(row)"
          >
            <el-icon><RefreshRight /></el-icon>
          </el-button>
          <el-button text type="primary" title="复制" @click="copyTask(row)">
            <el-icon><CopyDocument /></el-icon>
          </el-button>
          <el-button text type="danger" title="删除" @click="confirmDelete(row)">
            <el-icon><Delete /></el-icon>
          </el-button>
          <el-button v-if="row.result_url" text type="success" title="查看结果" @click="openResult(row)">
            <el-icon><VideoPlay /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh, CopyDocument, Delete, VideoPlay, RefreshRight } from '@element-plus/icons-vue'
import { api } from '../api/index.js'

const tasks = ref([])
const projects = ref([])
const loading = ref(false)
const filterProject = ref('')
const filterStatus = ref('')
const projectMap = ref({})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const getStatusType = (status) => {
  const types = { pending: 'warning', running: 'primary', success: 'success', failed: 'danger', queued: 'info' }
  return types[status] || 'info'
}

const getProjectName = (projectId) => {
  return projectMap.value[projectId] || projectId
}

const loadProjects = async () => {
  try {
    const list = await api.listProjects(true)
    projects.value = list
    projectMap.value = {}
    for (const p of list) {
      projectMap.value[p.id] = p.name
    }
  } catch (e) {
    ElMessage.error('加载项目失败: ' + e.message)
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    tasks.value = await api.listTasks({
      project_id: filterProject.value || undefined,
      status: filterStatus.value || undefined
    })
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

const retryTask = (task) => {
  ElMessageBox.confirm(
    `确定重试任务 ${task.id}？将重置为 queued 状态并重新提交。`,
    '重试任务',
    { type: 'warning' }
  ).then(async () => {
    try {
      await api.retryTask(task.id)
      ElMessage.success('任务已重新入队')
      loadTasks()
    } catch (e) {
      ElMessage.error('重试失败: ' + e.message)
    }
  }).catch(() => {})
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

watch([filterProject, filterStatus], loadTasks)

onMounted(() => {
  loadProjects()
  loadTasks()
})
</script>

<style scoped>
.admin-tasks {
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
.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
</style>