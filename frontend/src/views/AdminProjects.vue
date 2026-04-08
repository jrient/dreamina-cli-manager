<!-- frontend/src/views/AdminProjects.vue -->
<template>
  <div class="admin-projects">
    <div class="page-header">
      <el-button text @click="$router.push('/admin')">
        <el-icon><ArrowLeft /></el-icon>
        返回 Admin
      </el-button>
      <h2>项目管理</h2>
    </div>

    <el-table :data="projects" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="120" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="deleted_at" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.deleted_at ? 'danger' : 'success'">
            {{ row.deleted_at ? '已删除' : '活跃' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button text type="primary" @click="showEditDialog(row)">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button v-if="row.deleted_at" text type="success" @click="restoreProject(row)">
            <el-icon><RefreshRight /></el-icon>
            恢复
          </el-button>
          <el-button v-if="row.deleted_at" text type="danger" @click="permanentDelete(row)">
            <el-icon><Delete /></el-icon>
            彻底删除
          </el-button>
          <el-button v-if="!row.deleted_at" text type="danger" @click="softDelete(row)">
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑对话框 -->
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
import { ArrowLeft, Edit, RefreshRight, Delete } from '@element-plus/icons-vue'
import { api } from '../api/index.js'

const projects = ref([])
const loading = ref(false)
const editDialogVisible = ref(false)
const editForm = ref({ id: '', name: '' })

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const loadProjects = async () => {
  loading.value = true
  try {
    projects.value = await api.listProjects(true)
  } catch (e) {
    ElMessage.error('加载项目失败: ' + e.message)
  }
  loading.value = false
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

const softDelete = (project) => {
  ElMessageBox.confirm(`确定软删除项目 "${project.name}"?`, '删除项目', { type: 'warning' })
    .then(async () => {
      try {
        await api.deleteProject(project.id)
        ElMessage.success('项目已删除')
        loadProjects()
      } catch (e) {
        ElMessage.error('删除失败: ' + e.message)
      }
    }).catch(() => {})
}

const restoreProject = async (project) => {
  try {
    await api.restoreProject(project.id)
    ElMessage.success('项目已恢复')
    loadProjects()
  } catch (e) {
    ElMessage.error('恢复失败: ' + e.message)
  }
}

const permanentDelete = (project) => {
  ElMessageBox.confirm(
    `确定彻底删除项目 "${project.name}"? 此操作不可恢复，素材将被删除。`,
    '彻底删除',
    { type: 'warning' }
  ).then(async () => {
    try {
      await api.deleteProject(project.id, true)
      ElMessage.success('项目已彻底删除')
      loadProjects()
    } catch (e) {
      ElMessage.error('删除失败: ' + e.message)
    }
  }).catch(() => {})
}

onMounted(loadProjects)
</script>

<style scoped>
.admin-projects {
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
</style>