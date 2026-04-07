<!-- frontend/src/views/SubmitTask.vue -->
<template>
  <el-card class="submit-card">
    <template #header>提交 Multimodal2Video 任务</template>

    <el-form :model="form" label-width="100px" @submit.prevent="submit">

      <!-- Images -->
      <el-form-item label="图片">
        <el-upload
          v-model:file-list="form.images"
          list-type="picture-card"
          :auto-upload="false"
          :limit="9"
          accept="image/*"
          multiple
          :on-exceed="() => ElMessage.warning('最多 9 张图片')"
        >
          <el-icon><Plus /></el-icon>
          <template #tip>
            <div class="el-upload__tip">最多 9 张，至少 1 张图片或视频</div>
          </template>
        </el-upload>
      </el-form-item>

      <!-- Audio -->
      <el-form-item label="音频">
        <el-upload
          v-model:file-list="form.audios"
          :auto-upload="false"
          :limit="3"
          accept="audio/*"
          multiple
          :on-exceed="() => ElMessage.warning('最多 3 个音频')"
        >
          <el-button type="primary" plain>选择音频</el-button>
          <template #tip><div class="el-upload__tip">最多 3 个，时长需 2-15 秒</div></template>
        </el-upload>
      </el-form-item>

      <!-- Videos -->
      <el-form-item label="参考视频">
        <el-upload
          v-model:file-list="form.videos"
          :auto-upload="false"
          :limit="3"
          accept="video/*"
          multiple
          :on-exceed="() => ElMessage.warning('最多 3 个视频')"
        >
          <el-button type="primary" plain>选择视频</el-button>
          <template #tip><div class="el-upload__tip">最多 3 个</div></template>
        </el-upload>
      </el-form-item>

      <!-- Prompt -->
      <el-form-item label="提示词">
        <el-input v-model="form.prompt" type="textarea" :rows="3" placeholder="可选：描述生成内容" />
      </el-form-item>

      <!-- Duration -->
      <el-form-item label="时长 (秒)">
        <el-slider v-model="form.duration" :min="4" :max="15" :step="1" show-input style="width: 340px" />
      </el-form-item>

      <!-- Ratio -->
      <el-form-item label="比例">
        <el-radio-group v-model="form.ratio">
          <el-radio-button v-for="r in ratios" :key="r" :label="r">{{ r }}</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- Model -->
      <el-form-item label="模型版本">
        <el-select v-model="form.model_version" style="width: 220px">
          <el-option v-for="m in models" :key="m.value" :label="m.label" :value="m.value" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="submitting" :disabled="!accountId">
          提交任务
        </el-button>
        <el-text v-if="!accountId" type="warning" style="margin-left: 12px">请先选择账号</el-text>
      </el-form-item>

    </el-form>
  </el-card>
</template>

<script setup>
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/index.js'

const router = useRouter()
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
    router.push('/tasks')
  } catch (e) {
    ElMessage.error('提交失败: ' + e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.submit-card { max-width: 780px; margin: 24px auto; }
</style>