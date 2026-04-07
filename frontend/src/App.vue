<!-- frontend/src/App.vue -->
<template>
  <el-container class="app-container">
    <el-header height="60px" class="app-header">
      <div class="header-left">
        <span class="app-title">🎬 Dreamina 视频生成</span>
      </div>
      <div class="header-center">
        <AccountSelector />
      </div>
      <div class="header-right">
        <el-button text @click="$router.push('/accounts')">账号管理</el-button>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, provide } from 'vue'
import AccountSelector from './components/AccountSelector.vue'

const selectedAccountId = ref('')
provide('selectedAccountId', selectedAccountId)
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
.app-main {
  padding: 0;
  overflow: hidden;
}
</style>