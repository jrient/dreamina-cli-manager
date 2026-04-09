<!-- frontend/src/App.vue -->
<template>
  <el-container class="app-container">
    <el-header height="60px" class="app-header">
      <div class="header-left">
        <span class="app-title">🎬 Dreamina 视频生成</span>
      </div>
      <div class="header-center">
        <AccountSelector v-if="authStore.isLoggedIn" />
      </div>
      <div class="header-right">
        <template v-if="authStore.isLoggedIn">
          <el-button text @click="$router.push('/projects')">项目</el-button>
          <el-button text @click="$router.push('/accounts')">账号管理</el-button>
          <el-button v-if="authStore.isAdmin" text @click="$router.push('/admin')">Admin</el-button>
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              {{ authStore.user?.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, provide, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import AccountSelector from './components/AccountSelector.vue'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const selectedAccountId = ref('')
provide('selectedAccountId', selectedAccountId)

onMounted(async () => {
  await authStore.fetchUser()
})

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style>
body { margin: 0; }
.app-container { min-height: 100vh; }
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1e1e2e;
  border-bottom: none;
  padding: 0 20px;
}
.app-title {
  font-size: 18px;
  font-weight: bold;
  color: #fff;
}
.header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.user-dropdown {
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}
.app-main {
  padding: 0;
  overflow: hidden;
}
</style>