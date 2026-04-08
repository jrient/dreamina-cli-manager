<!-- frontend/src/views/ProjectTasks.vue -->
<template>
  <div class="project-tasks">
    <!-- 顶部导航栏 -->
    <div class="page-header">
      <el-button text @click="$router.push('/projects')">
        <el-icon><ArrowLeft /></el-icon>
        返回项目列表
      </el-button>
      <h2>{{ project?.name || '...' }}</h2>
      <el-button type="primary" @click="$router.push(`/projects/${projectId}/materials`)">
        <el-icon><FolderOpened /></el-icon>
        素材
      </el-button>
    </div>

    <!-- 左右分栏 -->
    <div class="split-layout">
      <div class="left-panel">
        <SubmitTask :project-id="projectId" @submitted="loadTasks" />
      </div>
      <div class="right-panel">
        <!-- 任务列表头部 -->
        <div class="list-header">
          <div class="header-title">
            <el-text size="large">任务列表</el-text>
            <el-text size="small" type="info">（共 {{ tasks.length }} 条）</el-text>
          </div>
          <div class="header-actions">
            <el-tag
              v-for="s in statusOptions"
              :key="s.value"
              :type="activeStatus === s.value ? 'primary' : 'info'"
              :effect="activeStatus === s.value ? 'dark' : 'plain'"
              class="filter-tag"
              @click="activeStatus = s.value"
            >
              {{ s.label }}
            </el-tag>
            <el-button :loading="loading" circle size="small" @click="loadTasks">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <el-empty v-if="!filteredTasks.length && !loading" description="暂无任务" />

        <el-card
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-card"
          :data-status="task.status"
          shadow="hover"
        >
          <!-- 第一行：账号、标签、时间、操作 -->
          <div class="task-header">
            <span class="task-account">{{ task.account_id }}</span>
            <el-tag v-if="task.label" size="small" type="warning" effect="plain">{{ task.label }}</el-tag>
            <span class="task-time">
              {{ formatDate(task.created_at) }}
              <template v-if="task.status === 'success' || task.status === 'failed'">
                → {{ formatDate(task.updated_at) }}
              </template>
            </span>
            <el-button text type="primary" @click="copyTask(task)">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
            <el-button type="danger" text @click="confirmDelete(task)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>

          <!-- 第二行：提示词 -->
          <div v-if="task.prompt" class="task-prompt">
            <el-text size="small">{{ task.prompt }}</el-text>
          </div>

          <!-- 第三行：参数 + 下载 -->
          <div class="task-params-row">
            <el-text v-if="task.params" type="info" size="small">{{ formatParams(task.params) }}</el-text>
            <el-link v-if="task.status === 'success' && task.result_url" :href="task.result_url" target="_blank" type="success" size="small">
              <el-icon><Download /></el-icon> 下载视频
            </el-link>
          </div>

          <!-- 第四行：ID、状态、错误 -->
          <div class="task-footer">
            <el-text type="info" size="small">ID: {{ task.id }}</el-text>
            <el-tag :type="statusType(task.status)" size="small">{{ statusLabel(task.status) }}</el-tag>
            <el-text v-if="task.status === 'failed'" type="danger" size="small" class="task-error-inline">
              {{ task.error_msg || '任务失败，原因未知' }}
            </el-text>
          </div>
          <el-alert
            v-if="task.status === 'failed' && task.error_msg && task.error_msg.includes('ComplianceConfirmation')"
            title="请先在 Dreamina Web 端完成合规授权后重试"
            type="warning"
            show-icon
            :closable="false"
            style="margin-top: 6px"
          />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, FolderOpened, Refresh, CopyDocument, Delete, Download } from '@element-plus/icons-vue'
import { api } from '../api/index.js'
import SubmitTask from './SubmitTask.vue'

const route = useRoute()
const projectId = computed(() => route.params.id)

const project = ref(null)
const tasks = ref([])
const loading = ref(false)
const activeStatus = ref('')
let refreshTimer = null

const statusOptions = [
  { label: '全部', value: '' },
  { label: '排队中', value: 'queued' },
  { label: '等待中', value: 'pending' },
  { label: '生成中', value: 'processing' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' },
]

const filteredTasks = computed(() => {
  if (!activeStatus.value) return tasks.value
  return tasks.value.filter(t => t.status === activeStatus.value)
})

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const statusType = (s) => {
  return { queued: 'info', pending: 'info', processing: 'warning', success: 'success', failed: 'danger' }[s] || 'info'
}

const statusLabel = (s) => {
  return { queued: '排队中', pending: '等待中', processing: '生成中', success: '已完成', failed: '失败' }[s] || s
}

const formatParams = (paramsStr) => {
  try {
    const p = JSON.parse(paramsStr)
    return `${p.ratio} · ${p.duration}s · ${p.model_version}`
  } catch {
    return paramsStr
  }
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
  } finally {
    loading.value = false
  }
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

onMounted(() => {
  loadProject()
  loadTasks()
  refreshTimer = setInterval(loadTasks, 10000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style scoped>
.project-tasks {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.page-header h2 {
  margin: 0;
  flex: 1;
}

.split-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0;
}

.left-panel {
  width: 42%;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  padding: 16px;
}

.right-panel {
  width: 58%;
  background: #f5f7fa;
  overflow-y: auto;
  padding: 16px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.header-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-tag {
  cursor: pointer;
  margin-right: 4px;
}

.task-card {
  margin-bottom: 12px;
  border-left: 3px solid;
}

.task-card[data-status="success"] { border-left-color: #67c23a; }
.task-card[data-status="processing"] { border-left-color: #e6a23c; }
.task-card[data-status="failed"] { border-left-color: #f56c6c; }
.task-card[data-status="pending"] { border-left-color: #909399; }
.task-card[data-status="queued"] { border-left-color: #c0c4cc; }

.task-card :deep(.el-card__body) { padding: 12px 16px; }
.task-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.task-account { font-size: 13px; font-weight: 500; color: #303133; }
.task-time { flex: 1; font-size: 12px; color: #909399; }
.task-prompt { margin: 4px 0; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-params-row { display: flex; align-items: center; gap: 12px; margin: 4px 0; }
.task-footer { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.task-error-inline { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
