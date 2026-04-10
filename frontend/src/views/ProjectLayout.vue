<template>
  <div class="project-layout">
    <div class="project-nav">
      <el-button text @click="$router.push('/projects')">
        <el-icon><ArrowLeft /></el-icon>
        项目列表
      </el-button>
      <span class="project-title">{{ project?.name || '...' }}</span>
      <el-tabs v-model="activeTab" @tab-change="onTabChange" class="nav-tabs">
        <el-tab-pane label="任务" name="tasks" />
        <el-tab-pane label="素材" name="materials" />
        <el-tab-pane v-if="canManage" label="设置" name="settings" />
      </el-tabs>
    </div>
    <div class="project-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { api } from '../api/index.js'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()

const authStore = useAuthStore()
const project = ref(null)
const projectId = computed(() => route.params.id)
const canManage = computed(() => authStore.isAdmin || project.value?.my_role === 'owner')

const activeTab = computed(() => {
  const path = route.name
  if (path === 'project-materials') return 'materials'
  if (path === 'project-settings') return 'settings'
  return 'tasks'
})

const onTabChange = (tab) => {
  router.push(`/projects/${projectId.value}/${tab}`)
}

const loadProject = async () => {
  try {
    project.value = await api.getProject(projectId.value)
  } catch (e) {
    // ignore
  }
}

onMounted(loadProject)
watch(projectId, loadProject)
</script>

<style scoped>
.project-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.project-nav {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.project-title {
  font-size: 16px;
  font-weight: bold;
  white-space: nowrap;
}

.nav-tabs {
  flex: 1;
}

.nav-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.nav-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.project-content {
  flex: 1;
  overflow: auto;
}
</style>
