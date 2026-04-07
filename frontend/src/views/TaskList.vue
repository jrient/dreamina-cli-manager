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
      <div class="task-header">
        <el-tag :type="statusType(task.status)">{{ statusLabel(task.status) }}</el-tag>
        <span class="task-meta">{{ task.account_id }} · {{ formatDate(task.created_at) }}</span>
        <el-button type="danger" text @click="deleteTask(task.id)">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <div class="task-params" v-if="task.params">
        <el-text type="info" size="small">
          {{ formatParams(task.params) }}
        </el-text>
      </div>

      <div v-if="task.prompt" class="task-prompt">
        <el-text size="small">{{ task.prompt }}</el-text>
      </div>

      <div v-if="task.status === 'success' && task.result_url" class="task-result">
        <el-link :href="task.result_url" target="_blank" type="primary">
          <el-icon><VideoPlay /></el-icon> 下载/查看视频
        </el-link>
      </div>

      <div v-if="task.status === 'failed'" class="task-error">
        <el-text type="danger" size="small">{{ task.error_msg }}</el-text>
        <el-alert
          v-if="task.error_msg && task.error_msg.includes('ComplianceConfirmation')"
          title="请先在 Dreamina Web 端完成合规授权后重试"
          type="warning"
          show-icon
          :closable="false"
          style="margin-top: 8px"
        />
      </div>

      <div class="task-id">
        <el-text type="info" size="small">ID: {{ task.id }}</el-text>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete, VideoPlay } from '@element-plus/icons-vue'
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
  { label: '等待中', value: 'pending' },
  { label: '生成中', value: 'processing' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' },
]

onMounted(async () => {
  await fetchTasks()
  await fetchAccounts()
  refreshTimer = setInterval(fetchTasks, 10000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})

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

function statusType(s) {
  return { pending: 'info', processing: 'warning', success: 'success', failed: 'danger' }[s] || 'info'
}

function statusLabel(s) {
  return { pending: '等待中', processing: '生成中', success: '已完成', failed: '失败' }[s] || s
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

.task-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.task-meta { flex: 1; color: #909399; font-size: 13px; }
.task-params { margin-bottom: 4px; }
.task-prompt { margin: 6px 0; }
.task-result { margin-top: 10px; }
.task-error { margin-top: 8px; }
.task-id { margin-top: 8px; }
</style>