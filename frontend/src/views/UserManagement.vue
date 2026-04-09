<template>
  <div class="user-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showCreateDialog">新建用户</el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading">
        <el-table-column prop="username" label="用户名" />
        <el-table-column label="管理员" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_admin" type="success">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button size="small" @click="showResetPassword(row)">重置密码</el-button>
            <el-button
              v-if="!row.is_admin"
              size="small"
              type="warning"
              @click="setAdmin(row, true)"
            >
              设为管理员
            </el-button>
            <el-button
              v-if="row.is_admin"
              size="small"
              type="info"
              @click="setAdmin(row, false)"
            >
              取消管理员
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteUser(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建用户对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建用户" width="400px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createUser" :loading="createLoading">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <el-form :model="resetForm" :rules="resetRules" ref="resetFormRef">
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="resetPassword" :loading="resetLoading">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const users = ref([])
const loading = ref(false)

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref()
const createForm = reactive({ username: '', password: '' })
const createRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const resetDialogVisible = ref(false)
const resetLoading = ref(false)
const resetFormRef = ref()
const resetForm = reactive({ userId: '', password: '' })
const resetRules = {
  password: [{ required: true, message: '请输入新密码', trigger: 'blur' }]
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/users')
    users.value = response.data
  } catch (err) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  createForm.username = ''
  createForm.password = ''
  createDialogVisible.value = true
}

const createUser = async () => {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  createLoading.value = true
  try {
    await axios.post('/api/users', createForm)
    ElMessage.success('用户创建成功')
    createDialogVisible.value = false
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    createLoading.value = false
  }
}

const showResetPassword = (row) => {
  resetForm.userId = row.id
  resetForm.password = ''
  resetDialogVisible.value = true
}

const resetPassword = async () => {
  const valid = await resetFormRef.value.validate().catch(() => false)
  if (!valid) return

  resetLoading.value = true
  try {
    await axios.put(`/api/users/${resetForm.userId}`, { password: resetForm.password })
    ElMessage.success('密码重置成功')
    resetDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '重置失败')
  } finally {
    resetLoading.value = false
  }
}

const setAdmin = async (row, isAdmin) => {
  try {
    await axios.put(`/api/users/${row.id}`, { is_admin: isAdmin })
    ElMessage.success(isAdmin ? '已设为管理员' : '已取消管理员')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

const deleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户 "${row.username}"？`, '确认删除', {
      type: 'warning'
    })
    await axios.delete(`/api/users/${row.id}`)
    ElMessage.success('用户已删除')
    fetchUsers()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '删除失败')
    }
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(fetchUsers)
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>