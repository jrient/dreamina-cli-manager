<!-- frontend/src/views/AdminEntry.vue -->
<template>
  <div class="admin-entry">
    <div class="page-header">
      <el-button text @click="$router.push('/projects')">
        <el-icon><ArrowLeft /></el-icon>
        返回项目列表
      </el-button>
      <h2>Admin 管理</h2>
    </div>

    <div class="admin-nav">
      <el-card class="nav-card" @click="$router.push('/admin/projects')" shadow="hover">
        <el-icon class="nav-icon"><FolderOpened /></el-icon>
        <div class="nav-title">项目管理</div>
        <div class="nav-desc">管理所有项目（含已删除），恢复或彻底删除</div>
      </el-card>

      <el-card class="nav-card" @click="$router.push('/admin/accounts')" shadow="hover">
        <el-icon class="nav-icon"><User /></el-icon>
        <div class="nav-title">账号配置</div>
        <div class="nav-desc">管理账号登录和余额</div>
      </el-card>

      <el-card class="nav-card" @click="$router.push('/admin/tasks')" shadow="hover">
        <el-icon class="nav-icon"><List /></el-icon>
        <div class="nav-title">全局任务</div>
        <div class="nav-desc">查看所有任务，按项目筛选</div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ArrowLeft, FolderOpened, User, List } from '@element-plus/icons-vue'
</script>

<style scoped>
.admin-entry {
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
.admin-nav {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
.nav-card {
  cursor: pointer;
  text-align: center;
  padding: 24px;
}
.nav-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}
.nav-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 8px;
}
.nav-desc {
  color: #909399;
  font-size: 14px;
}
</style>