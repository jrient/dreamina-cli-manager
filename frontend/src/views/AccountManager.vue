<!-- frontend/src/views/AccountManager.vue -->
<template>
  <div class="account-manager">
    <div class="page-header">
      <el-text size="large">账号管理</el-text>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 新增账号
      </el-button>
    </div>

    <!-- 账号列表 -->
    <el-table :data="accounts" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="账号 ID" width="200" />
      <el-table-column label="登录状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.logged_in ? 'success' : 'danger'">
            {{ row.logged_in ? '已登录' : '未登录' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="任务数量" width="120">
        <template #default="{ row }">
          <span v-if="taskCounts[row.id]">
            <template v-if="taskCounts[row.id].queued > 0">
              {{ taskCounts[row.id].active }}+{{ taskCounts[row.id].queued }}
            </template>
            <template v-else-if="taskCounts[row.id].active > 0">
              {{ taskCounts[row.id].active }}
            </template>
            <span v-else style="color: #909399">-</span>
          </span>
          <span v-else style="color: #909399">-</span>
        </template>
      </el-table-column>
      <el-table-column label="积分余额" width="150">
        <template #default="{ row }">
          <span v-if="row.credit">{{ formatCredit(row.credit) }}</span>
          <span v-else-if="row.logged_in">
            <el-button text type="primary" size="small" @click="refreshCredit(row.id)">查询</el-button>
          </span>
          <span v-else style="color: #909399">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="350" fixed="right">
        <template #default="{ row }">
          <el-button-group>
            <el-button
              size="small"
              type="primary"
              @click="startLogin(row)"
              v-if="!row.logged_in"
            >
              登录
            </el-button>
            <el-button
              size="small"
              @click="refreshCredit(row.id)"
              :loading="refreshingId === row.id"
              v-if="row.logged_in"
            >
              刷新积分
            </el-button>
            <el-button
              size="small"
              type="warning"
              @click="logoutAccount(row.id)"
              v-if="row.logged_in"
            >
              退出登录
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteAccount(row.id)"
            >
              删除
            </el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增账号对话框 -->
    <el-dialog v-model="showCreateDialog" title="新增账号" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="账号 ID">
          <el-input
            v-model="createForm.account_id"
            placeholder="例如: alice, bob, 我的账号"
            @keyup.enter="createAccount"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createAccount" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 登录对话框 -->
    <el-dialog v-model="showLoginDialog" title="账号登录" width="600px" :close-on-click-modal="false">
      <div v-if="loginStep === 1">
        <el-alert type="info" :closable="false" style="margin-bottom: 16px">
          <template #title>
            <strong>登录步骤：</strong>
          </template>
          <ol style="margin: 8px 0 0 0; padding-left: 20px;">
            <li>点击下方「登录链接」在浏览器中登录即梦账号</li>
            <li>登录成功后，点击「获取凭证 JSON」链接</li>
            <li>复制页面显示的完整 JSON 内容</li>
            <li>将 JSON 粘贴到下方输入框并点击「导入凭证」</li>
          </ol>
        </el-alert>

        <el-space direction="vertical" style="width: 100%">
          <div>
            <el-text tag="b">1. 登录链接：</el-text>
            <el-link :href="loginData.login_url" target="_blank" type="primary" style="margin-left: 8px">
              点击打开登录页面
            </el-link>
          </div>
          <div>
            <el-text tag="b">2. 获取凭证 JSON：</el-text>
            <el-link :href="loginData.json_url" target="_blank" type="primary" style="margin-left: 8px">
              点击获取 JSON
            </el-link>
            <el-text type="info" size="small" style="margin-left: 8px">
              （登录后打开此链接）
            </el-text>
          </div>
        </el-space>

        <el-divider />

        <el-text tag="b">3. 粘贴凭证 JSON：</el-text>
        <el-input
          v-model="credentialsJson"
          type="textarea"
          :rows="8"
          placeholder="将从「获取凭证 JSON」链接复制的 JSON 粘贴到这里..."
          style="margin-top: 8px"
        />
      </div>

      <div v-else-if="loginStep === 2" style="text-align: center; padding: 20px">
        <el-icon size="48" color="#67C23A"><CircleCheck /></el-icon>
        <el-text size="large" style="display: block; margin-top: 16px">
          登录成功！
        </el-text>
        <el-text type="info" style="display: block; margin-top: 8px">
          账号积分: {{ loginResult.credit }}
        </el-text>
      </div>

      <template #footer>
        <el-button @click="showLoginDialog = false">关闭</el-button>
        <el-button
          v-if="loginStep === 1"
          type="primary"
          @click="importCredentials"
          :loading="importing"
          :disabled="!credentialsJson.trim()"
        >
          导入凭证
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const accounts = ref([])
const taskCounts = ref({})
const loading = ref(false)
const refreshingId = ref(null)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ account_id: '' })

const showLoginDialog = ref(false)
const loginStep = ref(1)
const loginData = ref({ account_id: '', login_url: '', json_url: '' })
const credentialsJson = ref('')
const importing = ref(false)
const loginResult = ref({})

onMounted(() => {
  fetchAccounts()
  fetchTaskCounts()
})

async function fetchTaskCounts() {
  try {
    const resp = await fetch('/api/tasks/counts')
    if (resp.ok) taskCounts.value = await resp.json()
  } catch (e) {
    // ignore
  }
}

async function fetchAccounts() {
  loading.value = true
  try {
    const resp = await fetch('/api/accounts')
    if (!resp.ok) throw new Error('Failed to fetch accounts')
    accounts.value = await resp.json()
  } catch (e) {
    ElMessage.error('加载账号失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function refreshCredit(accountId) {
  refreshingId.value = accountId
  try {
    const resp = await fetch(`/api/accounts/${accountId}/refresh-credit`, { method: 'POST' })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to refresh credit')
    }
    const data = await resp.json()
    const account = accounts.value.find(a => a.id === accountId)
    if (account) account.credit = data.credit
    ElMessage.success(`积分: ${data.credit}`)
  } catch (e) {
    ElMessage.error('查询积分失败: ' + e.message)
  } finally {
    refreshingId.value = null
  }
}

async function createAccount() {
  if (!createForm.value.account_id.trim()) {
    ElMessage.warning('请输入账号 ID')
    return
  }
  creating.value = true
  try {
    const resp = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: createForm.value.account_id.trim() })
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to create account')
    }
    ElMessage.success('账号创建成功')
    showCreateDialog.value = false
    createForm.value.account_id = ''
    await fetchAccounts()
  } catch (e) {
    ElMessage.error('创建失败: ' + e.message)
  } finally {
    creating.value = false
  }
}

async function deleteAccount(accountId) {
  try {
    await ElMessageBox.confirm(
      `确认删除账号 "${accountId}"？删除后需要重新登录。`,
      '删除确认',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    const resp = await fetch(`/api/accounts/${accountId}`, { method: 'DELETE' })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to delete account')
    }
    ElMessage.success('账号已删除')
    await fetchAccounts()
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

async function logoutAccount(accountId) {
  try {
    await ElMessageBox.confirm(
      `确认退出账号 "${accountId}"？退出后需要重新登录。`,
      '退出登录',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    const resp = await fetch(`/api/accounts/${accountId}/logout`, { method: 'POST' })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to logout')
    }
    ElMessage.success('已退出登录')
    await fetchAccounts()
  } catch (e) {
    ElMessage.error('退出失败: ' + e.message)
  }
}

async function startLogin(account) {
  try {
    const resp = await fetch(`/api/accounts/${account.id}/start-login`, { method: 'POST' })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to start login')
    }
    loginData.value = await resp.json()
    loginData.value.account_id = account.id
    loginStep.value = 1
    credentialsJson.value = ''
    showLoginDialog.value = true
  } catch (e) {
    ElMessage.error('启动登录失败: ' + e.message)
  }
}

async function importCredentials() {
  if (!credentialsJson.value.trim()) {
    ElMessage.warning('请粘贴凭证 JSON')
    return
  }

  importing.value = true
  try {
    const resp = await fetch(`/api/accounts/${loginData.value.account_id}/import-credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_id: loginData.value.account_id,
        credentials_json: credentialsJson.value.trim()
      })
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to import credentials')
    }
    const result = await resp.json()
    loginResult.value = result
    loginStep.value = 2
    ElMessage.success('登录成功！')
    await fetchAccounts()
  } catch (e) {
    ElMessage.error('导入失败: ' + e.message)
  } finally {
    importing.value = false
  }
}

function formatCredit(credit) {
  try {
    const data = JSON.parse(credit)
    return data.total_credit || credit
  } catch {
    return credit
  }
}
</script>

<style scoped>
.account-manager { max-width: 1000px; margin: 24px auto; padding: 0 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
</style>