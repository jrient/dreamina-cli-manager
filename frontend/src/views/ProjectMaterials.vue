<!-- frontend/src/views/ProjectMaterials.vue -->
<template>
  <div class="project-materials">
    <div class="page-header">
      <el-button text @click="$router.push('/projects')">
        <el-icon><ArrowLeft /></el-icon>
        返回项目列表
      </el-button>
      <h2>{{ project?.name || '...' }} - 素材</h2>
      <el-button type="primary" @click="$router.push(`/projects/${projectId}/tasks`)">
        <el-icon><List /></el-icon>
        任务
      </el-button>
    </div>

    <!-- 图片素材区 -->
    <div class="material-section">
      <div class="section-header">
        <h3><el-icon><Picture /></el-icon> 图片素材</h3>
        <el-upload
          :action="uploadUrl"
          :data="{ name: uploadForm.name, type: 'image' }"
          :before-upload="beforeImageUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :show-file-list="false"
          accept="image/*"
        >
          <el-button type="primary">
            <el-icon><Plus /></el-icon>
            上传图片
          </el-button>
        </el-upload>
      </div>
      <div class="material-grid" v-if="images.length">
        <el-card v-for="material in images" :key="material.id" class="material-card" shadow="hover">
          <el-image :src="getFileUrl(material.file_path)" fit="contain" class="material-thumb" />
          <div class="material-info">
            <span class="material-name">{{ material.name }}</span>
            <el-dropdown trigger="click">
              <el-button text size="small">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="showEditDialog(material)">编辑名称</el-dropdown-item>
                  <el-dropdown-item @click="confirmDelete(material)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="暂无图片素材" :image-size="60" />
    </div>

    <!-- 音频素材区 -->
    <div class="material-section">
      <div class="section-header">
        <h3><el-icon><Headset /></el-icon> 音频素材</h3>
        <el-upload
          :action="uploadUrl"
          :data="{ name: uploadForm.name, type: 'audio' }"
          :before-upload="beforeAudioUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :show-file-list="false"
          accept="audio/*"
        >
          <el-button type="primary">
            <el-icon><Plus /></el-icon>
            上传音频
          </el-button>
        </el-upload>
      </div>
      <div class="material-list" v-if="audios.length">
        <div v-for="material in audios" :key="material.id" class="audio-item">
          <el-icon class="audio-icon"><Headset /></el-icon>
          <span class="material-name">{{ material.name }}</span>
          <audio :src="getFileUrl(material.file_path)" controls class="audio-player" />
          <el-dropdown trigger="click">
            <el-button text size="small">
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showEditDialog(material)">编辑名称</el-dropdown-item>
                <el-dropdown-item @click="confirmDelete(material)">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <el-empty v-else description="暂无音频素材" :image-size="60" />
    </div>

    <!-- 上传前输入名称对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传素材" width="400px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="素材名称">
          <el-input v-model="uploadForm.name" placeholder="请输入素材名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">确定上传</el-button>
      </template>
    </el-dialog>

    <!-- 编辑素材对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑素材" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="素材名称">
          <el-input v-model="editForm.name" placeholder="请输入素材名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updateMaterial">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, List, Picture, Headset, Plus, MoreFilled } from '@element-plus/icons-vue'
import { api } from '../api/index.js'

const route = useRoute()
const projectId = computed(() => route.params.id)

const project = ref(null)
const images = ref([])
const audios = ref([])
const uploadDialogVisible = ref(false)
const editDialogVisible = ref(false)
const uploadForm = ref({ name: '', type: '', file: null })
const editForm = ref({ id: '', name: '' })
const pendingUpload = ref(null)

const uploadUrl = computed(() => `/api/projects/${projectId.value}/materials`)

const getFileUrl = (filePath) => {
  // 文件路径是绝对路径，需要转换为 URL
  const fileName = filePath.split('/').pop()
  return `/uploads/materials/${fileName}`
}

const loadProject = async () => {
  try {
    project.value = await api.getProject(projectId.value)
  } catch (e) {
    ElMessage.error('加载项目失败: ' + e.message)
  }
}

const loadMaterials = async () => {
  try {
    const all = await api.listMaterials(projectId.value)
    images.value = all.filter(m => m.type === 'image')
    audios.value = all.filter(m => m.type === 'audio')
  } catch (e) {
    ElMessage.error('加载素材失败: ' + e.message)
  }
}

const beforeImageUpload = (file) => {
  uploadForm.value.type = 'image'
  uploadForm.value.name = file.name.split('.')[0]
  pendingUpload.value = file
  uploadDialogVisible.value = true
  return false // 阻止自动上传，等待确认
}

const beforeAudioUpload = (file) => {
  uploadForm.value.type = 'audio'
  uploadForm.value.name = file.name.split('.')[0]
  pendingUpload.value = file
  uploadDialogVisible.value = true
  return false // 阻止自动上传，等待确认
}

const confirmUpload = async () => {
  if (!uploadForm.value.name.trim()) {
    ElMessage.warning('请输入素材名称')
    return
  }
  uploadDialogVisible.value = false

  const formData = new FormData()
  formData.append('name', uploadForm.value.name.trim())
  formData.append('type', uploadForm.value.type)
  formData.append('file', pendingUpload.value)

  try {
    await api.createMaterial(projectId.value, formData)
    ElMessage.success('素材上传成功')
    loadMaterials()
  } catch (e) {
    ElMessage.error('上传失败: ' + e.message)
  }
}

const onUploadSuccess = () => {
  ElMessage.success('素材上传成功')
  loadMaterials()
}

const onUploadError = (err) => {
  ElMessage.error('上传失败: ' + err.message)
}

const showEditDialog = (material) => {
  editForm.value.id = material.id
  editForm.value.name = material.name
  editDialogVisible.value = true
}

const updateMaterial = async () => {
  if (!editForm.value.name.trim()) {
    ElMessage.warning('请输入素材名称')
    return
  }
  try {
    await api.updateMaterial(projectId.value, editForm.value.id, editForm.value.name.trim())
    ElMessage.success('素材更新成功')
    editDialogVisible.value = false
    loadMaterials()
  } catch (e) {
    ElMessage.error('更新失败: ' + e.message)
  }
}

const confirmDelete = (material) => {
  ElMessageBox.confirm(`确定删除素材 "${material.name}"?`, '删除素材', { type: 'warning' })
    .then(async () => {
      try {
        await api.deleteMaterial(projectId.value, material.id)
        ElMessage.success('素材已删除')
        loadMaterials()
      } catch (e) {
        ElMessage.error('删除失败: ' + e.message)
      }
    }).catch(() => {})
}

onMounted(() => {
  loadProject()
  loadMaterials()
})
</script>

<style scoped>
.project-materials {
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
.material-section {
  margin-bottom: 32px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}
.material-card {
  text-align: center;
}
.material-thumb {
  width: 100%;
  height: auto;
  max-height: 200px;
}
.material-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}
.material-name {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.audio-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 8px;
}
.audio-icon {
  font-size: 24px;
  color: #409eff;
}
.audio-player {
  height: 32px;
  flex: 1;
}
</style>