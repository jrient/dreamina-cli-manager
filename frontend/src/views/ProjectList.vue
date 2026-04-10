<!-- frontend/src/views/ProjectList.vue -->
<template>
  <div class="project-list">
    <div class="page-header">
      <h2>项目列表</h2>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        创建项目
      </el-button>
    </div>

    <div class="project-grid" v-if="projects.length">
      <el-card
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        shadow="hover"
        @click="$router.push(`/projects/${project.id}/tasks`)"
      >
        <div class="card-header">
          <span class="project-name">{{ project.name }}</span>
          <el-button
            v-if="project.my_role === 'owner' || isAdmin"
            text
            type="danger"
            size="small"
            @click.stop="confirmDelete(project)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="card-stats">
          <el-statistic title="任务数" :value="stats[project.id]?.task_count || 0" />
          <el-statistic title="素材数" :value="stats[project.id]?.material_count || 0" />
        </div>
        <div class="card-info">
          <p v-if="project.creator_name">拥有者: {{ project.creator_name }}</p>
          <p v-if="project.episode_count">集数: {{ project.episode_count }}</p>
          <p>更新: {{ formatDate(project.updated_at) }}</p>
        </div>
      </el-card>
    </div>

    <el-empty v-else description="暂无项目，点击创建按钮添加" />

    <!-- 创建项目对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建项目" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="项目名称">
          <el-input v-model="createForm.name" placeholder="请输入项目名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createProject">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth.js'
import { api } from '../api/index.js'

const authStore = useAuthStore()
const isAdmin = authStore.isAdmin

const projects = ref([])
const stats = ref({})
const createDialogVisible = ref(false)
const createForm = ref({ name: '' })

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const loadProjects = async () => {
  try {
    projects.value = await api.listProjects()
    for (const project of projects.value) {
      stats.value[project.id] = await api.getProjectStats(project.id)
    }
  } catch (e) {
    ElMessage.error('加载项目失败: ' + e.message)
  }
}

const showCreateDialog = (e) => {
  e.stopPropagation()
  createForm.value.name = ''
  createDialogVisible.value = true
}

const createProject = async () => {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  try {
    await api.createProject(createForm.value.name.trim())
    ElMessage.success('项目创建成功')
    createDialogVisible.value = false
    loadProjects()
  } catch (e) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const confirmDelete = (project) => {
  ElMessageBox.confirm(
    `确定删除项目 "${project.name}"？任务和素材将保留。`,
    '删除项目',
    { type: 'warning' }
  ).then(async () => {
    try {
      await api.deleteProject(project.id)
      ElMessage.success('项目已删除')
      loadProjects()
    } catch (e) {
      ElMessage.error('删除失败: ' + e.message)
    }
  }).catch(() => {})
}

onMounted(loadProjects)
</script>

<style scoped>
.project-list {
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
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
.project-card {
  height: 100%;
  cursor: pointer;
  transition: transform 0.15s ease;
}
.project-card:hover {
  transform: translateY(-2px);
}
.card-header {
  margin-bottom: 16px;
}
.project-name {
  font-size: 16px;
  font-weight: bold;
}
.card-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}
.card-info {
  color: #909399;
  font-size: 12px;
}
.card-info p {
  margin: 4px 0;
}
</style>
