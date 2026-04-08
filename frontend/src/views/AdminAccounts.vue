<!-- frontend/src/views/AdminAccounts.vue -->
<template>
  <div class="admin-accounts">
    <div class="page-header">
      <el-button text @click="$router.push('/admin')">
        <el-icon><ArrowLeft /></el-icon>
        返回 Admin
      </el-button>
      <h2>账号配置</h2>
    </div>

    <!-- 使用 AccountManager 组件 -->
    <AccountManager />
  </div>
</template>

<script setup>
import { ArrowLeft } from '@element-plus/icons-vue'
import AccountManager from './AccountManager.vue'
</script>

<style scoped>
.admin-accounts {
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