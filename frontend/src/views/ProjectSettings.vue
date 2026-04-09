<template>
  <div class="project-settings">
    <el-card v-loading="loading">
      <el-tabs v-model="activeTab">
        <!-- 基本设置 -->
        <el-tab-pane label="基本设置" name="basic">
          <el-form :model="settings" label-width="100px">
            <el-form-item label="集数配置">
              <el-select v-model="settings.episode_count" @change="saveSettings">
                <el-option
                  v-for="n in 100"
                  :key="n"
                  :label="n"
                  :value="n"
                />
              </el-select>
              <span style="margin-left: 10px; color: #909399;">任务分集范围 1-{{ settings.episode_count }}</span>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 账号配置 -->
        <el-tab-pane label="账号配置" name="accounts">
          <div class="section">
            <div class="section-title">项目账号池</div>
            <el-select
              v-model="projectAccounts"
              multiple
              placeholder="选择可用账号"
              style="width: 100%;"
              @change="saveProjectAccounts"
            >
              <el-option
                v-for="account in allAccounts"
                :key="account.id"
                :label="account.id"
                :value="account.id"
              />
            </el-select>
          </div>
        </el-tab-pane>

        <!-- 协作者管理 -->
        <el-tab-pane label="协作者管理" name="members">
          <div class="section">
            <div class="section-header">
              <span class="section-title">协作者列表</span>
              <el-button type="primary" size="small" @click="showAddMemberDialog">添加协作者</el-button>
            </div>

            <el-table :data="members" size="small">
              <el-table-column prop="username" label="用户名" />
              <el-table-column prop="role" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.role === 'owner'" type="success">拥有者</el-tag>
                  <el-tag v-else>协作者</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="可用账号">
                <template #default="{ row }">
                  <span v-if="row.role === 'owner'">全部</span>
                  <span v-else>{{ row.accounts.join(', ') || '未分配' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <template v-if="row.role !== 'owner'">
                    <el-button size="small" @click="showAccountDialog(row)">配置账号</el-button>
                    <el-button size="small" type="danger" @click="removeMember(row)">移除</el-button>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 添加协作者对话框 -->
    <el-dialog v-model="addMemberDialogVisible" title="添加协作者" width="400px">
      <el-select v-model="selectedUserId" placeholder="选择用户" style="width: 100%;">
        <el-option
          v-for="user in availableUsers"
          :key="user.id"
          :label="user.username"
          :value="user.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addMember" :loading="addMemberLoading">添加</el-button>
      </template>
    </el-dialog>

    <!-- 配置账号对话框 -->
    <el-dialog v-model="accountDialogVisible" title="配置可用账号" width="400px">
      <el-select v-model="selectedAccounts" multiple placeholder="选择账号" style="width: 100%;">
        <el-option
          v-for="account in projectAccounts"
          :key="account"
          :label="account"
          :value="account"
        />
      </el-select>
      <template #footer>
        <el-button @click="accountDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMemberAccounts" :loading="accountLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const projectId = route.params.id

const loading = ref(false)
const activeTab = ref('basic')

const settings = reactive({ episode_count: 50 })
const projectAccounts = ref([])
const members = ref([])
const allAccounts = ref([])
const allUsers = ref([])

// 添加协作者
const addMemberDialogVisible = ref(false)
const addMemberLoading = ref(false)
const selectedUserId = ref('')

// 配置账号
const accountDialogVisible = ref(false)
const accountLoading = ref(false)
const selectedMemberId = ref('')
const selectedAccounts = ref([])

const availableUsers = computed(() => {
  const memberIds = new Set(members.value.map(m => m.user_id))
  return allUsers.value.filter(u => !memberIds.has(u.id))
})

const fetchData = async () => {
  loading.value = true
  try {
    // 获取项目信息
    const projectRes = await axios.get(`/api/projects/${projectId}`)
    settings.episode_count = projectRes.data.episode_count || 50

    // 获取项目账号
    const accountsRes = await axios.get(`/api/projects/${projectId}/accounts`)
    projectAccounts.value = accountsRes.data

    // 获取成员
    const membersRes = await axios.get(`/api/projects/${projectId}/members`)
    members.value = membersRes.data

    // 获取所有即梦账号
    const allAccountsRes = await axios.get('/api/accounts')
    allAccounts.value = allAccountsRes.data

    // 获取所有用户
    const usersRes = await axios.get('/api/users')
    allUsers.value = usersRes.data
  } catch (err) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  try {
    await axios.put(`/api/projects/${projectId}/settings`, {
      episode_count: settings.episode_count
    })
    ElMessage.success('设置已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  }
}

const saveProjectAccounts = async () => {
  try {
    await axios.put(`/api/projects/${projectId}/accounts`, {
      accounts: projectAccounts.value
    })
    ElMessage.success('账号池已更新')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  }
}

const showAddMemberDialog = () => {
  selectedUserId.value = ''
  addMemberDialogVisible.value = true
}

const addMember = async () => {
  if (!selectedUserId.value) {
    ElMessage.warning('请选择用户')
    return
  }

  addMemberLoading.value = true
  try {
    await axios.post(`/api/projects/${projectId}/members`, {
      user_id: selectedUserId.value,
      role: 'collaborator'
    })
    ElMessage.success('协作者已添加')
    addMemberDialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  } finally {
    addMemberLoading.value = false
  }
}

const showAccountDialog = (row) => {
  selectedMemberId.value = row.user_id
  selectedAccounts.value = [...row.accounts]
  accountDialogVisible.value = true
}

const saveMemberAccounts = async () => {
  accountLoading.value = true
  try {
    await axios.put(`/api/projects/${projectId}/member-accounts/${selectedMemberId.value}`, {
      accounts: selectedAccounts.value
    })
    ElMessage.success('账号已分配')
    accountDialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    accountLoading.value = false
  }
}

const removeMember = async (row) => {
  try {
    await ElMessageBox.confirm(`确定移除协作者 "${row.username}"？`, '确认', { type: 'warning' })
    await axios.delete(`/api/projects/${projectId}/members/${row.user_id}`)
    ElMessage.success('协作者已移除')
    fetchData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '移除失败')
    }
  }
}

onMounted(fetchData)
</script>

<style scoped>
.project-settings {
  padding: 20px;
}

.section {
  margin-bottom: 20px;
}

.section-title {
  font-weight: bold;
  margin-bottom: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
</style>