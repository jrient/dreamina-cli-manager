<!-- frontend/src/views/SubmitTask.vue -->
<template>
  <div class="submit-panel">
    <div class="panel-title">
      <el-tag type="primary" effect="dark" size="small">NEW</el-tag>
      <span>提交任务</span>
    </div>

    <el-form :model="form" label-width="70px" label-position="top" @submit.prevent="submit">
      <!-- 媒体上传区：合并为一个上传按钮组 -->
      <el-form-item label="">
        <div class="upload-area">
          <div class="upload-hint">拖拽或点击上传媒体文件</div>
          <div class="upload-buttons">
            <el-button plain @click="triggerUpload('image')">🖼️ 图片</el-button>
            <el-button plain @click="triggerUpload('audio')">🎵 音频</el-button>
            <el-button plain @click="triggerUpload('video')">🎬 视频</el-button>
          </div>
          <div class="upload-preview">
            <el-tag v-for="(img, i) in form.images" :key="i" closable @close="removeFile('images', i)">
              🖼️ 图片{{ i + 1 }}: {{ img.name }}
            </el-tag>
            <el-tag v-for="(aud, i) in form.audios" :key="i" closable @close="removeFile('audios', i)">
              🎵 音频{{ i + 1 }}: {{ aud.name }}
            </el-tag>
            <el-tag v-for="(vid, i) in form.videos" :key="i" closable @close="removeFile('videos', i)">
              🎬 视频{{ i + 1 }}: {{ vid.name }}
            </el-tag>
          </div>
        </div>
        <!-- 隐藏的 file input -->
        <input ref="imageInput" type="file" accept="image/*" multiple hidden @change="handleUpload('images', $event)">
        <input ref="audioInput" type="file" accept="audio/*" multiple hidden @change="handleUpload('audios', $event)">
        <input ref="videoInput" type="file" accept="video/*" multiple hidden @change="handleUpload('videos', $event)">
      </el-form-item>

      <!-- 提示词输入框 -->
      <el-form-item label="提示词">
        <el-input
          v-model="form.prompt"
          type="textarea"
          :rows="3"
          placeholder="可选：描述生成内容（输入 @ 引用已上传文件）"
        />
      </el-form-item>

      <!-- 参数行：横向排列 -->
      <div class="params-row">
        <el-form-item label="时长">
          <el-slider v-model="form.duration" :min="4" :max="15" :step="1" show-input />
        </el-form-item>
        <el-form-item label="比例">
          <el-radio-group v-model="form.ratio">
            <el-radio-button v-for="r in ratios" :key="r" :label="r">{{ r }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="模型">
          <el-select v-model="form.model_version">
            <el-option v-for="m in models" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="submitting" :disabled="!accountId">
          ▶ 提交任务
        </el-button>
        <el-text v-if="!accountId" type="warning" style="margin-left: 12px">请先选择账号</el-text>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/index.js'

const accountId = inject('selectedAccountId')

const ratios = ['1:1', '16:9', '9:16', '4:3', '3:4', '21:9']
const models = [
  { label: 'Seedance 2.0 Fast', value: 'seedance2.0fast' },
  { label: 'Seedance 2.0', value: 'seedance2.0' },
  { label: 'Seedance 2.0 VIP', value: 'seedance2.0_vip' },
  { label: 'Seedance 2.0 Fast VIP', value: 'seedance2.0fast_vip' },
]

const form = ref({
  images: [],
  audios: [],
  videos: [],
  prompt: '',
  duration: 5,
  ratio: '16:9',
  model_version: 'seedance2.0fast',
})
const submitting = ref(false)

const imageInput = ref(null)
const audioInput = ref(null)
const videoInput = ref(null)

function triggerUpload(type) {
  if (type === 'image') imageInput.value.click()
  else if (type === 'audio') audioInput.value.click()
  else if (type === 'video') videoInput.value.click()
}

function handleUpload(type, event) {
  const files = Array.from(event.target.files)
  const current = form.value[type]
  files.forEach(file => {
    current.push({ name: file.name, raw: file })
  })
  event.target.value = ''
}

function removeFile(type, index) {
  form.value[type].splice(index, 1)
}

async function submit() {
  if (!form.value.images.length && !form.value.videos.length) {
    ElMessage.error('至少需要 1 张图片或 1 个参考视频')
    return
  }

  const fd = new FormData()
  fd.append('account_id', accountId.value)
  fd.append('prompt', form.value.prompt)
  fd.append('duration', form.value.duration)
  fd.append('ratio', form.value.ratio)
  fd.append('model_version', form.value.model_version)

  form.value.images.forEach(f => fd.append('images', f.raw))
  form.value.audios.forEach(f => fd.append('audios', f.raw))
  form.value.videos.forEach(f => fd.append('videos', f.raw))

  submitting.value = true
  try {
    const task = await api.submitTask(fd)
    ElMessage.success(`任务已提交，ID: ${task.id}`)
    form.value.images = []
    form.value.audios = []
    form.value.videos = []
    form.value.prompt = ''
  } catch (e) {
    ElMessage.error('提交失败: ' + e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.upload-area {
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  background: #fafafa;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}

.upload-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 10px;
}

.upload-preview {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.params-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.params-row .el-form-item {
  flex: 1;
  min-width: 120px;
}
</style>