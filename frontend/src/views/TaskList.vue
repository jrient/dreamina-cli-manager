<!-- frontend/src/views/TaskList.vue -->
<template>
  <div class="task-list">
    <!-- 筛选器头部 -->
    <div class="list-header">
      <div class="header-title">
        <el-text size="large">任务列表</el-text>
        <el-text size="small" type="info">（共 {{ tasks.length }} 条）</el-text>
      </div>
      <div class="header-actions">
        <!-- 状态筛选：Tag 按钮组 -->
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
        <!-- 账号筛选：下拉框 -->
        <el-select
          v-model="activeAccount"
          placeholder="账号筛选"
          size="small"
          style="width: 120px; margin-left: 10px"
          clearable
        >
          <el-option label="全部账号" value="" />
          <el-option v-for="acc in accounts" :key="acc.id" :label="acc.id" :value="acc.id" />
        </el-select>
        <el-button :loading="loading" circle size="small" @click="fetchTasks">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <el-empty v-if="!tasks.length && !loading" description="暂无任务" />

    <el-card
      v-for="task in tasks"
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
        <el-button
          v-if="task.status === 'failed'"
          text
          type="warning"
          title="重试"
          @click="retryTask(task)"
        >
          <el-icon><RefreshRight /></el-icon>
        </el-button>
        <el-button type="danger" text title="删除" @click="deleteTask(task.id)">
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
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete, Download, RefreshRight } from '@element-plus/icons-vue'
import { api } from '../api/index.js'

const tasks = ref([])
const loading = ref(false)
const accounts = ref([])
let refreshTimer = null

// 筛选状态
const activeStatus = ref('')
const activeAccount = ref('')

const statusOptions = [
  { label: '全部', value: '' },
  { label: '排队中', value: 'queued' },
  { label: '已提交', value: 'pending' },
  { label: '生成中', value: 'processing' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' },
]

onMounted(async () => {
  await fetchTasks()
  await fetchAccounts()
  scheduleRefresh()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearTimeout(refreshTimer)
  }
})

// 动态轮询：有活跃任务时 5 秒，否则 30 秒
function scheduleRefresh() {
  const activeCount = tasks.value.filter(t =>
    ['queued', 'pending', 'processing'].includes(t.status)
  ).length
  const interval = activeCount > 0 ? 5000 : 30000
  refreshTimer = setTimeout(async () => {
    await fetchTasks()
    scheduleRefresh()
  }, interval)
}

// 监听筛选条件变化
watch([activeStatus, activeAccount], () => {
  fetchTasks()
})

async function fetchAccounts() {
  try {
    accounts.value = await api.listAccounts()
  } catch (e) {
    // 静默失败
  }
}

async function fetchTasks() {
  loading.value = true
  try {
    tasks.value = await api.listTasks({
      status: activeStatus.value || undefined,
      account_id: activeAccount.value || undefined,
    })
  } catch (e) {
    ElMessage.error('加载任务失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function deleteTask(id) {
  await ElMessageBox.confirm('确认删除该任务记录？', '提示', { type: 'warning' })
  try {
    await api.deleteTask(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

function retryTask(task) {
  ElMessageBox.confirm(
    `确定重试任务 ${task.id}？将重置为 queued 并重新提交。`,
    '重试任务',
    { type: 'warning' }
  ).then(async () => {
    try {
      await api.retryTask(task.id)
      ElMessage.success('任务已重新入队')
      fetchTasks()
    } catch (e) {
      ElMessage.error('重试失败: ' + e.message)
    }
  }).catch(() => {})
}

function statusType(s) {
  return { queued: 'info', pending: 'info', processing: 'warning', success: 'success', failed: 'danger' }[s] || 'info'
}

function statusLabel(s) {
  return { queued: '排队中', pending: '已提交', processing: '生成中', success: '已完成', failed: '失败' }[s] || s
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function formatParams(paramsStr) {
  try {
    const p = JSON.parse(paramsStr)
    return `${p.ratio} · ${p.duration}s · ${p.model_version}`
  } catch {
    return paramsStr
  }
}
</script>

<style scoped>
.task-list { max-width: 860px; margin: 24px auto; }

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