<!-- frontend/src/views/ProjectTasks.vue -->
<template>
  <div class="project-tasks">
    <!-- 左右分栏 -->
    <div class="split-layout">
      <div class="left-panel">
        <SubmitTask ref="submitTaskRef" :project-id="projectId" @submitted="loadTasks" />
      </div>
      <div class="right-panel">
        <!-- 任务列表头部 -->
        <div class="list-header">
          <div class="header-title">
            <el-text size="large">任务列表</el-text>
            <el-text size="small" type="info">（共 {{ tasks.length }} 条）</el-text>
          </div>
          <div class="header-actions">
            <!-- 集数筛选 -->
            <el-select v-model="filterEpisode" placeholder="全部集数" clearable size="small" style="width:130px" v-if="episodeOptions.length">
              <el-option v-for="ep in episodeOptions" :key="ep.value" :label="ep.label" :value="ep.value" />
            </el-select>
            <!-- 账号筛选 -->
            <el-select v-model="filterAccount" placeholder="全部账号" clearable size="small" style="width:130px" v-if="accountOptions.length">
              <el-option v-for="acc in accountOptions" :key="acc" :label="acc" :value="acc" />
            </el-select>
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
            <el-button size="small" type="success" :disabled="selectedTaskIds.size === 0" @click="batchDownload">
              <el-icon><Download /></el-icon>
              批量下载({{ selectedTaskIds.size }})
            </el-button>
            <el-button v-if="activeStatus === 'success'" size="small" @click="selectAll">
              {{ isAllSelected ? '取消全选' : '全选' }}
            </el-button>
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
          <!-- 第一行：创建者、集数、标签、时间、操作 -->
          <div class="task-header">
            <el-checkbox
              v-if="activeStatus === 'success'"
              :model-value="selectedTaskIds.has(task.id)"
              @change="toggleSelect(task.id)"
              @click.stop
            />
            <span class="task-creator">{{ task.creator_name || task.account_id }}</span>
            <el-tag v-if="task.episode" size="small" type="info" effect="plain">第{{ task.episode }}集</el-tag>
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
            <el-link v-if="task.status === 'success' && task.result_url" :href="`/api/tasks/${task.id}/download`" type="success" size="small">
              <el-icon><Download /></el-icon> 下载视频
            </el-link>
          </div>

          <!-- 第四行：ID、账号、状态 -->
          <div class="task-footer">
            <el-text type="info" size="small">ID: {{ task.id }}</el-text>
            <el-text type="info" size="small">账号: {{ task.account_id }}</el-text>
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
import { Refresh, CopyDocument, Delete, Download } from '@element-plus/icons-vue'
import { api } from '../api/index.js'
import SubmitTask from './SubmitTask.vue'

const route = useRoute()
const projectId = computed(() => route.params.id)

const tasks = ref([])
const loading = ref(false)
const activeStatus = ref('')
let refreshTimer = null
const submitTaskRef = ref(null)

const project = ref(null)
const filterEpisode = ref(null)
const filterAccount = ref('')
const selectedTaskIds = ref(new Set())

const statusOptions = [
  { label: '全部', value: '' },
  { label: '排队中', value: 'queued' },
  { label: '已提交', value: 'pending' },
  { label: '生成中', value: 'processing' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' },
]

const accountOptions = computed(() => {
  const ids = [...new Set(tasks.value.map(t => t.account_id).filter(Boolean))]
  return ids
})

const episodeOptions = computed(() => {
  const count = project.value?.episode_count || 0
  return Array.from({ length: count }, (_, i) => {
    const ep = i + 1
    const epTasks = tasks.value.filter(t => t.episode === ep)
    const success = epTasks.filter(t => t.status === 'success').length
    return { value: ep, label: `${ep} [${success}/${epTasks.length}]` }
  })
})

const filteredTasks = computed(() => {
  let list = tasks.value
  if (activeStatus.value) list = list.filter(t => t.status === activeStatus.value)
  if (filterEpisode.value) list = list.filter(t => t.episode === filterEpisode.value)
  if (filterAccount.value) list = list.filter(t => t.account_id === filterAccount.value)
  return list
})

const successTaskIds = computed(() => {
  return filteredTasks.value.filter(t => t.status === 'success' && t.result_url).map(t => t.id)
})

const isAllSelected = computed(() => {
  if (successTaskIds.value.length === 0) return false
  return successTaskIds.value.every(id => selectedTaskIds.value.has(id))
})

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const statusType = (s) => {
  return { queued: 'info', pending: 'info', processing: 'warning', success: 'success', failed: 'danger' }[s] || 'info'
}

const statusLabel = (s) => {
  return { queued: '排队中', pending: '已提交', processing: '生成中', success: '已完成', failed: '失败' }[s] || s
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
  } catch (e) {}
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

const toggleSelect = (taskId) => {
  const s = new Set(selectedTaskIds.value)
  s.has(taskId) ? s.delete(taskId) : s.add(taskId)
  selectedTaskIds.value = s
}

const selectAll = () => {
  if (isAllSelected.value) {
    // 取消全选
    const s = new Set(selectedTaskIds.value)
    successTaskIds.value.forEach(id => s.delete(id))
    selectedTaskIds.value = s
  } else {
    // 全选
    selectedTaskIds.value = new Set([...selectedTaskIds.value, ...successTaskIds.value])
  }
}

const batchDownload = async () => {
  const toDownload = filteredTasks.value.filter(
    t => t.status === 'success' && t.result_url && selectedTaskIds.value.has(t.id)
  )
  if (!toDownload.length) {
    ElMessage.warning('请先勾选已完成的任务')
    return
  }
  for (const task of toDownload) {
    const a = document.createElement('a')
    a.href = `/api/tasks/${task.id}/download`
    a.download = ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    await new Promise(r => setTimeout(r, 300))
  }
}

const copyTask = async (task) => {
  if (submitTaskRef.value) {
    await submitTaskRef.value.fillForm(task)
    document.querySelector('.left-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
  flex-wrap: wrap;
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
.task-creator { font-size: 13px; font-weight: 500; color: #303133; }
.task-time { flex: 1; font-size: 12px; color: #909399; }
.task-prompt { margin: 4px 0; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-params-row { display: flex; align-items: center; gap: 12px; margin: 4px 0; }
.task-footer { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.task-error-inline { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
