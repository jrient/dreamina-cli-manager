<!-- frontend/src/views/SubmitTask.vue -->
<template>
  <div class="submit-panel">
    <div class="panel-title">✨ 创建新任务</div>

    <el-form :model="form" label-position="top" @submit.prevent="submit">
      <!-- 项目和标签 -->
      <div class="project-row" v-if="showProjectFields">
        <el-form-item label="项目" class="project-select-item">
          <el-select v-model="form.project_id" placeholder="选择项目" clearable>
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签" class="label-input-item">
          <el-input v-model="form.label" placeholder="可选标签" maxlength="50" show-word-limit />
        </el-form-item>
      </div>

      <!-- 媒体上传区：卡片化设计 -->
      <div class="section-label">媒体文件</div>
      <div class="upload-grid">
        <div class="upload-card" @click="triggerUpload('image')" @mouseenter="hoverCard = 'image'" @mouseleave="hoverCard = ''">
          <div class="upload-icon">🖼️</div>
          <div class="upload-label">添加图片</div>
          <div class="upload-limit">最多9张</div>
        </div>
        <div class="upload-card" @click="triggerUpload('audio')" @mouseenter="hoverCard = 'audio'" @mouseleave="hoverCard = ''">
          <div class="upload-icon">🎵</div>
          <div class="upload-label">添加音频</div>
          <div class="upload-limit">最多3个</div>
        </div>
        <div class="upload-card" @click="triggerUpload('video')" @mouseenter="hoverCard = 'video'" @mouseleave="hoverCard = ''">
          <div class="upload-icon">🎬</div>
          <div class="upload-label">添加视频</div>
          <div class="upload-limit">最多3个</div>
        </div>
      </div>

      <!-- 已上传文件预览 -->
      <div class="file-preview" v-if="hasFiles">
        <div v-for="(img, i) in form.images" :key="'img-'+i" class="preview-item">
          <div class="preview-thumb preview-thumb-image">
            <img v-if="img.preview" :src="img.preview" class="thumb-img" />
            <span v-else class="thumb-icon">🖼️</span>
          </div>
          <div class="preview-name">{{ img.name }}</div>
          <div class="preview-remove" @click="removeFile('images', i)">✕</div>
        </div>
        <div v-for="(aud, i) in form.audios" :key="'aud-'+i" class="preview-item">
          <div class="preview-thumb preview-thumb-audio">
            <span class="thumb-icon">🎵</span>
          </div>
          <div class="preview-name">{{ aud.name }}</div>
          <div class="preview-remove" @click="removeFile('audios', i)">✕</div>
        </div>
        <div v-for="(vid, i) in form.videos" :key="'vid-'+i" class="preview-item">
          <div class="preview-thumb preview-thumb-video">
            <span class="thumb-icon">🎬</span>
          </div>
          <div class="preview-name">{{ vid.name }}</div>
          <div class="preview-remove" @click="removeFile('videos', i)">✕</div>
        </div>
      </div>

      <!-- 隐藏的 file input -->
      <input ref="imageInput" type="file" accept="image/*" multiple hidden @change="handleUpload('images', $event)">
      <input ref="audioInput" type="file" accept="audio/*" multiple hidden @change="handleUpload('audios', $event)">
      <input ref="videoInput" type="file" accept="video/*" multiple hidden @change="handleUpload('videos', $event)">

      <!-- 提示词输入框 -->
      <div class="section-label">
        提示词
        <span class="section-hint">（可选，输入@引用媒体）</span>
      </div>
      <div class="prompt-container" ref="promptContainer">
        <div
          ref="promptEditor"
          contenteditable="true"
          class="prompt-editor"
          data-placeholder="描述你想要生成的视频内容..."
          @input="handleEditorInput"
          @keydown.esc="showMentionPopup = false"
        ></div>
        <!-- @ 浮层 -->
        <div v-if="showMentionPopup" class="mention-popup">
          <div v-if="form.images.length" class="mention-group">
            <div class="group-title">图片</div>
            <div
              v-for="(img, i) in form.images"
              :key="i"
              class="mention-item"
              @click="insertMention('图片', i + 1)"
            >
              <div class="mention-thumb">
                <img v-if="img.preview" :src="img.preview" class="mention-thumb-img" />
                <span v-else>🖼️</span>
              </div>
              <span>图片{{ i + 1 }} <span class="filename">{{ img.name }}</span></span>
            </div>
          </div>
          <div v-if="form.audios.length" class="mention-group">
            <div class="group-title">音频</div>
            <div
              v-for="(aud, i) in form.audios"
              :key="i"
              class="mention-item"
              @click="insertMention('音频', i + 1)"
            >
              <span>🎵 音频{{ i + 1 }} <span class="filename">{{ aud.name }}</span></span>
            </div>
          </div>
          <div v-if="form.videos.length" class="mention-group">
            <div class="group-title">视频</div>
            <div
              v-for="(vid, i) in form.videos"
              :key="i"
              class="mention-item"
              @click="insertMention('视频', i + 1)"
            >
              <span>🎬 视频{{ i + 1 }} <span class="filename">{{ vid.name }}</span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成参数区 -->
      <div class="params-section">
        <div class="section-label">生成参数</div>

        <!-- 时长滑块 -->
        <div class="param-row">
          <div class="param-header">
            <span class="param-label">视频时长</span>
            <span class="param-value">{{ form.duration }} 秒</span>
          </div>
          <el-slider v-model="form.duration" :min="4" :max="15" :step="1" :show-tooltip="false" />
        </div>

        <!-- 比例选择 -->
        <div class="param-row">
          <span class="param-label">画面比例</span>
          <div class="ratio-chips">
            <span
              v-for="r in ratios"
              :key="r"
              :class="['ratio-chip', { active: form.ratio === r }]"
              @click="form.ratio = r"
            >{{ r }}</span>
          </div>
        </div>

        <!-- 模型选择 -->
        <div class="param-row">
          <span class="param-label">模型版本</span>
          <el-select v-model="form.model_version" class="model-select">
            <el-option v-for="m in models" :key="m.value" :label="m.label" :value="m.value">
              <span>{{ m.icon }} {{ m.label }}</span>
            </el-option>
          </el-select>
        </div>
      </div>

      <!-- 提交按钮 -->
      <el-button
        type="primary"
        native-type="submit"
        :loading="submitting"
        :disabled="!accountId"
        class="submit-btn"
      >
        ✨ 开始生成
      </el-button>
      <div v-if="!accountId" class="submit-hint">请先在顶部选择账号</div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, inject, computed, onMounted, watch } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { api } from '../api/index.js'

const props = defineProps({
  projectId: { type: String, default: '' }
})
const emit = defineEmits(['submitted'])

const accountId = inject('selectedAccountId')

const ratios = ['1:1', '16:9', '9:16', '4:3', '3:4', '21:9']
const models = [
  { label: 'Fast（推荐）', value: 'seedance2.0fast', icon: '🚀' },
  { label: '标准版', value: 'seedance2.0', icon: '⭐' },
  { label: 'VIP', value: 'seedance2.0_vip', icon: '👑' },
  { label: 'Fast VIP', value: 'seedance2.0fast_vip', icon: '💎' },
]

const projects = ref([])
const form = ref({
  images: [],
  audios: [],
  videos: [],
  prompt: '',
  duration: 5,
  ratio: '16:9',
  model_version: 'seedance2.0fast',
  project_id: '',
  label: '',
})
const submitting = ref(false)
const hoverCard = ref('')

const showProjectFields = computed(() => props.projectId)

watch(() => props.projectId, (val) => {
  form.value.project_id = val
})

const hasFiles = computed(() => {
  return form.value.images.length || form.value.audios.length || form.value.videos.length
})

const imageInput = ref(null)
const audioInput = ref(null)
const videoInput = ref(null)
const promptEditor = ref(null)
const promptContainer = ref(null)
const showMentionPopup = ref(false)
const savedRange = ref(null)

onClickOutside(promptContainer, () => {
  showMentionPopup.value = false
})

function triggerUpload(type) {
  if (type === 'image') imageInput.value.click()
  else if (type === 'audio') audioInput.value.click()
  else if (type === 'video') videoInput.value.click()
}

function handleUpload(type, event) {
  const files = Array.from(event.target.files)
  const current = form.value[type]
  files.forEach(file => {
    const item = { name: file.name, raw: file }
    // 为图片生成预览 URL
    if (type === 'images' && file.type.startsWith('image/')) {
      item.preview = URL.createObjectURL(file)
    }
    current.push(item)
  })
  event.target.value = ''
}

function removeFile(type, index) {
  const item = form.value[type][index]
  // 清理预览 URL
  if (item.preview) {
    URL.revokeObjectURL(item.preview)
  }
  form.value[type].splice(index, 1)
}

function handleEditorInput() {
  const selection = window.getSelection()
  if (!selection.rangeCount) return

  const range = selection.getRangeAt(0)
  const node = range.startContainer

  let atNode = null
  let atOffset = -1

  if (node.nodeType === Node.TEXT_NODE && node.textContent[range.startOffset - 1] === '@') {
    atNode = node
    atOffset = range.startOffset - 1
  } else if (node.nodeType === Node.ELEMENT_NODE) {
    // Empty editor or caret at element boundary
    const prev = node.childNodes[range.startOffset - 1]
    if (prev && prev.nodeType === Node.TEXT_NODE && prev.textContent.slice(-1) === '@') {
      atNode = prev
      atOffset = prev.textContent.length - 1
    }
  }

  if (atNode !== null) {
    const atRange = range.cloneRange()
    atRange.setStart(atNode, atOffset)
    atRange.setEnd(atNode, atOffset + 1)
    savedRange.value = atRange
    showMentionPopup.value = true
  } else {
    showMentionPopup.value = false
    savedRange.value = null
  }
}

function getPromptText() {
  const editor = promptEditor.value
  if (!editor) return ''
  let text = ''
  let isFirst = true
  function walk(node, isTopLevel) {
    if (node.nodeType === Node.TEXT_NODE) {
      text += node.textContent
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      const type = node.dataset?.refType
      if (type) {
        const index = node.dataset.refIndex
        const label = { image: '图片', audio: '音频', video: '视频' }[type] || type
        text += `@${label}${index}`
      } else if (node.tagName === 'BR') {
        text += '\n'
      } else if (isTopLevel && (node.tagName === 'DIV' || node.tagName === 'P')) {
        if (!isFirst) text += '\n'
        isFirst = false
        node.childNodes.forEach(child => walk(child, false))
      } else {
        node.childNodes.forEach(child => walk(child, false))
      }
    }
  }
  editor.childNodes.forEach(node => walk(node, true))
  return text.trim()
}

function insertMention(type, index) {
  const mention = `@${type}${index}`
  form.value.prompt = form.value.prompt.slice(0, -1) + mention + ' '
  showMentionPopup.value = false
}

async function submit() {
  if (!form.value.images.length && !form.value.videos.length) {
    ElMessage.error('至少需要 1 张图片或 1 个参考视频')
    return
  }

  const fd = new FormData()
  fd.append('account_id', accountId.value)
  fd.append('prompt', getPromptText())
  fd.append('duration', form.value.duration)
  fd.append('ratio', form.value.ratio)
  fd.append('model_version', form.value.model_version)
  if (form.value.project_id) fd.append('project_id', form.value.project_id)
  if (form.value.label) fd.append('label', form.value.label)

  form.value.images.forEach(f => fd.append('images', f.raw))
  form.value.audios.forEach(f => fd.append('audios', f.raw))
  form.value.videos.forEach(f => fd.append('videos', f.raw))

  submitting.value = true
  try {
    const task = await api.submitTask(fd)
    ElMessage.success(`任务已提交，ID: ${task.id}`)
    form.value.images.forEach(f => { if (f.preview) URL.revokeObjectURL(f.preview) })
    form.value.images = []
    form.value.audios = []
    form.value.videos = []
    if (promptEditor.value) promptEditor.value.innerHTML = ''
    form.value.label = ''
    emit('submitted')
  } catch (e) {
    ElMessage.error('提交失败: ' + e.message)
  } finally {
    submitting.value = false
  }
}

async function loadProjects() {
  try {
    projects.value = await api.listProjects()
  } catch (e) {
    // ignore
  }
}

onMounted(() => {
  if (props.projectId) {
    form.value.project_id = props.projectId
  } else {
    loadProjects()
  }
})
</script>

<style scoped>
.submit-panel {
  padding: 20px;
}

.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 20px;
}

.project-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.project-select-item, .label-input-item {
  flex: 1;
  margin-bottom: 0;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.section-hint {
  font-weight: 400;
  color: #909399;
  font-size: 11px;
}

/* 上传卡片网格 */
.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.upload-card {
  border: 2px dashed #c0c4cc;
  border-radius: 10px;
  padding: 16px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.upload-card:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.upload-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.upload-label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.upload-limit {
  font-size: 10px;
  color: #909399;
  margin-top: 2px;
}

/* 已上传文件预览 */
.file-preview {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.preview-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 6px 10px 6px 6px;
  max-width: 180px;
}

.preview-thumb {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.preview-thumb-image { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.preview-thumb-audio { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.preview-thumb-video { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }

.thumb-icon {
  font-size: 12px;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 6px;
}

.preview-name {
  font-size: 11px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-remove {
  width: 16px;
  height: 16px;
  background: #ff4d4f;
  border-radius: 50%;
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  margin-left: auto;
}

.preview-remove:hover {
  background: #ff7875;
}

/* 提示词 */
.prompt-container {
  position: relative;
  margin-bottom: 16px;
}

.prompt-editor {
  min-height: 72px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fafafa;
  font-size: 13px;
  line-height: 1.6;
  outline: none;
  word-break: break-word;
  white-space: pre-wrap;
  cursor: text;
}
.prompt-editor:focus {
  border-color: #409eff;
  background: #fff;
}
.prompt-editor:empty::before {
  content: attr(data-placeholder);
  color: #c0c4cc;
  pointer-events: none;
}
.prompt-ref {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 2px;
  background: #f0f7ff;
  border: 1px solid #d0e8ff;
  padding: 1px;
  user-select: none;
}
.prompt-ref img {
  width: 22px;
  height: 22px;
  object-fit: cover;
  display: block;
  border-radius: 3px;
}
.prompt-ref-icon {
  padding: 2px 4px;
  font-size: 14px;
  line-height: 1;
}

/* @ 浮层 */
.mention-popup {
  position: absolute;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 8px;
  z-index: 10;
  max-height: 200px;
  overflow-y: auto;
  width: 220px;
  top: 100%;
  left: 0;
  margin-top: 4px;
}

.mention-group {
  margin-bottom: 4px;
}

.group-title {
  color: #909399;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 8px;
}

.mention-item {
  padding: 6px 8px;
  cursor: pointer;
  border-radius: 6px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s;
}

.mention-thumb {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  overflow: hidden;
}

.mention-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mention-item:hover {
  background: #f0f7ff;
}

.filename {
  color: #909399;
  font-size: 10px;
}

/* 参数区 */
.params-section {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
}

.params-section .section-label {
  margin-bottom: 12px;
}

.param-row {
  margin-bottom: 14px;
}

.param-row:last-child {
  margin-bottom: 0;
}

.param-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.param-label {
  font-size: 12px;
  color: #606266;
}

.param-value {
  font-size: 12px;
  color: #409eff;
  font-weight: 600;
}

/* 比例选择芯片 */
.ratio-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.ratio-chip {
  padding: 4px 12px;
  border-radius: 14px;
  font-size: 11px;
  background: #e4e7ed;
  color: #606266;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ratio-chip:hover {
  background: #d3d4d6;
}

.ratio-chip.active {
  background: #409eff;
  color: #fff;
}

/* 模型选择 */
.model-select {
  width: 100%;
  margin-top: 8px;
}

.model-select :deep(.el-input__wrapper) {
  border-radius: 8px;
}

/* 提交按钮 */
.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(102, 126, 234, 0.4);
  transition: all 0.2s ease;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.submit-btn:active {
  transform: translateY(0);
}

.submit-btn:disabled {
  background: #c0c4cc;
  box-shadow: none;
}

.submit-hint {
  text-align: center;
  font-size: 12px;
  color: #e6a23c;
  margin-top: 8px;
}
</style>