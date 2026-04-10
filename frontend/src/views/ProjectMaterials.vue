<!-- frontend/src/views/ProjectMaterials.vue -->
<template>
  <div class="project-materials">
    <!-- 图片素材区 -->
    <div class="material-section">
      <div class="section-header">
        <h3><el-icon><Picture /></el-icon> 图片素材</h3>
        <div class="upload-actions">
          <el-upload
            :action="uploadUrl"
            :before-upload="(file) => beforeSingleUpload(file, 'image')"
            :on-success="onUploadSuccess"
            :on-error="onUploadError"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button>
              <el-icon><Plus /></el-icon>
              上传图片
            </el-button>
          </el-upload>
          <el-upload
            :action="uploadUrl"
            :before-upload="(file) => batchUpload(file, 'image')"
            :show-file-list="false"
            multiple
            accept="image/*"
          >
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              批量上传
            </el-button>
          </el-upload>
        </div>
      </div>
      <div class="material-grid" v-if="images.length">
        <el-card v-for="material in images" :key="material.id" class="material-card" shadow="hover">
          <el-image :src="getFileUrl(material.file_path)" fit="contain" class="material-thumb" />
          <div class="material-info">
            <el-input
              v-if="editingId === material.id"
              v-model="editingName"
              size="small"
              class="name-input"
              @blur="saveInlineName(material)"
              @keyup.enter="saveInlineName(material)"
              @keyup.esc="cancelEdit"
              ref="nameInputRef"
              autofocus
            />
            <span v-else class="material-name editable" @click="startEdit(material)" title="点击修改名称">
              {{ material.name }}
            </span>
            <el-button type="danger" text size="small" @click="confirmDelete(material)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="暂无图片素材" :image-size="60" />
    </div>

    <!-- 音频素材区 -->
    <div class="material-section">
      <div class="section-header">
        <h3><el-icon><Headset /></el-icon> 音频素材</h3>
        <div class="upload-actions">
          <el-upload
            :action="uploadUrl"
            :before-upload="(file) => beforeSingleUpload(file, 'audio')"
            :on-success="onUploadSuccess"
            :on-error="onUploadError"
            :show-file-list="false"
            accept="audio/*"
          >
            <el-button>
              <el-icon><Plus /></el-icon>
              上传音频
            </el-button>
          </el-upload>
          <el-upload
            :action="uploadUrl"
            :before-upload="(file) => batchUpload(file, 'audio')"
            :show-file-list="false"
            multiple
            accept="audio/*"
          >
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              批量上传
            </el-button>
          </el-upload>
        </div>
      </div>
      <div class="material-list" v-if="audios.length">
        <div v-for="material in audios" :key="material.id" class="audio-item">
          <el-icon class="audio-icon"><Headset /></el-icon>
          <el-input
            v-if="editingId === material.id"
            v-model="editingName"
            size="small"
            class="name-input-audio"
            @blur="saveInlineName(material)"
            @keyup.enter="saveInlineName(material)"
            @keyup.esc="cancelEdit"
            autofocus
          />
          <span v-else class="material-name editable" @click="startEdit(material)" title="点击修改名称">
            {{ material.name }}
          </span>
          <audio :src="getFileUrl(material.file_path)" controls class="audio-player" />
          <el-button type="danger" text size="small" @click="confirmDelete(material)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
      <el-empty v-else description="暂无音频素材" :image-size="60" />
    </div>

    <!-- 单文件上传 — 输入名称对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传素材" width="400px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="素材名称">
          <el-input v-model="uploadForm.name" placeholder="请输入素材名称" @keyup.enter="confirmUpload" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">确定上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, Headset, Plus, Upload, Delete } from '@element-plus/icons-vue'
import { api } from '../api/index.js'

const route = useRoute()
const projectId = computed(() => route.params.id)

const images = ref([])
const audios = ref([])
const uploadDialogVisible = ref(false)
const uploadForm = ref({ name: '', type: '', file: null })
const pendingUpload = ref(null)

// 内联编辑状态
const editingId = ref(null)
const editingName = ref('')

const uploadUrl = computed(() => `/api/projects/${projectId.value}/materials`)

const getFileUrl = (filePath) => {
  const fileName = filePath.split('/').pop()
  return `/uploads/materials/${fileName}`
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

// 单文件上传（弹窗确认名称）
const beforeSingleUpload = (file, type) => {
  uploadForm.value.type = type
  uploadForm.value.name = file.name.replace(/\.[^.]+$/, '')
  uploadForm.value.file = file
  pendingUpload.value = file
  uploadDialogVisible.value = true
  return false
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
    ElMessage.success('上传成功')
    loadMaterials()
  } catch (e) {
    ElMessage.error('上传失败: ' + e.message)
  }
}

// 批量上传（直接使用文件名，手动上传后拒绝 el-upload 自动上传）
const batchUpload = (file, type) => {
  const formData = new FormData()
  formData.append('name', file.name.replace(/\.[^.]+$/, ''))
  formData.append('type', type)
  formData.append('file', file)
  api.createMaterial(projectId.value, formData)
    .then(() => loadMaterials())
    .catch(() => ElMessage.error(`${file.name} 上传失败`))
  return false  // 同步返回 false，阻止 el-upload 自动上传
}

const onUploadSuccess = () => {
  ElMessage.success('上传成功')
  loadMaterials()
}

const onUploadError = (err) => {
  ElMessage.error('上传失败: ' + err.message)
}

// 内联编辑
const startEdit = (material) => {
  editingId.value = material.id
  editingName.value = material.name
}

const cancelEdit = () => {
  editingId.value = null
  editingName.value = ''
}

const saveInlineName = async (material) => {
  const name = editingName.value.trim()
  if (!name || name === material.name) {
    cancelEdit()
    return
  }
  try {
    await api.updateMaterial(projectId.value, material.id, name)
    material.name = name
  } catch (e) {
    ElMessage.error('更新失败: ' + e.message)
  }
  cancelEdit()
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
  loadMaterials()
})
</script>

<style scoped>
.project-materials {
  padding: 20px;
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
.upload-actions {
  display: flex;
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
  max-height: 120px;
}
.material-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0 0;
  gap: 4px;
}
.material-name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.editable {
  cursor: pointer;
  border-bottom: 1px dashed transparent;
  transition: border-color 0.2s;
}
.editable:hover {
  border-bottom-color: #409eff;
  color: #409eff;
}
.name-input {
  flex: 1;
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
  flex-shrink: 0;
}
.name-input-audio {
  width: 160px;
}
.audio-player {
  height: 32px;
  flex: 1;
}
</style>
