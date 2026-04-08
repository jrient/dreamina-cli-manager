<!-- frontend/src/views/ProjectList.vue -->
<template>
  <div class="project-list">
    <div class="page-header">
      <h2>项目列表</h2>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        创建项目
      </el-button>
      <el-button @click="$router.push('/admin')">
        <el-icon><Setting /></el-icon>
        Admin
      </el-button>
    </div>

    <div class="project-grid" v-if="projects.length">
      <el-card v-for="project in projects" :key="project.id" class="project-card" shadow="hover">
        <div class="card-header">
          <span class="project-name">{{ project.name }}</span>
          <el-dropdown trigger="click">
            <el-button text>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showEditDialog(project)">编辑名称</el-dropdown-item>
                <el-dropdown-item @click="confirmDelete(project)">删除项目</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="card-stats">
          <el-statistic title="任务数" :value="stats[project.id]?.task_count || 0" />
          <el-statistic title="素材数" :value="stats[project.id]?.material_count || 0" />
        </div>
        <div class="card-info">
          <p>创建: {{ formatDate(project.created_at) }}</p>
          <p>更新: {{ formatDate(project.updated_at) }}</p>
        </div>
        <div class="card-actions">
          <el-button type="primary" text @click="$router.push(`/projects/${project.id}/tasks`)">
            <el-icon><List /></el-icon>
            任务
          </el-button>
          <el-button type="primary" text @click="$router.push(`/projects/${project.id}/materials`)">
            <el-icon><FolderOpened /></el-icon>
            素材
          </el-button>
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

    <!-- 编辑项目对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑项目" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="项目名称">
          <el-input v-model="editForm.name" placeholder="请输入项目名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updateProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Setting, MoreFilled, List, FolderOpened } from '@element-plus/icons-vue'
import { api } from '../api/index.js'

const projects = ref([])
const stats = ref({})
const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const createForm = ref({ name: '' })
const editForm = ref({ id: '', name: '' })

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const loadProjects = async () => {
  try {
    projects.value = await api.listProjects()
    // 加载每个项目的统计
    for (const project of projects.value) {
      stats.value[project.id] = await api.getProjectStats(project.id)
    }
  } catch (e) {
    ElMessage.error('加载项目失败: ' + e.message)
  }
}

const showCreateDialog = () => {
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

const showEditDialog = (project) => {
  editForm.value.id = project.id
  editForm.value.name = project.name
  editDialogVisible.value = true
}

const updateProject = async () => {
  if (!editForm.value.name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  try {
    await api.updateProject(editForm.value.id, editForm.value.name.trim())
    ElMessage.success('项目更新成功')
    editDialogVisible.value = false
    loadProjects()
  } catch (e) {
    ElMessage.error('更新失败: ' + e.message)
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
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  margin-bottom: 16px;
}
.card-info p {
  margin: 4px 0;
}
.card-actions {
  display: flex;
  gap: 12px;
}
</style>