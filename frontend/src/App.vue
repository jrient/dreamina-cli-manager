<!-- frontend/src/App.vue -->
<template>
  <el-container class="app-container">
    <el-header height="60px" class="app-header">
      <div class="header-left">
        <span class="app-title">Dreamina 视频生成</span>
      </div>
      <div class="header-center">
        <AccountSelector />
      </div>
      <div class="header-right">
        <el-menu mode="horizontal" :router="true" :default-active="$route.path">
          <el-menu-item index="/">提交任务</el-menu-item>
          <el-menu-item index="/tasks">任务列表</el-menu-item>
          <el-menu-item index="/accounts">账号管理</el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, provide } from 'vue'
import AccountSelector from './components/AccountSelector.vue'

// Provide selected account ID to child components
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
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}
.app-title { font-size: 18px; font-weight: bold; color: #303133; }
</style>