# UI 第二轮优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 Dreamina Web UI 为左右分栏布局，增加任务筛选器和提示词 @ 媒体引用功能

**Architecture:** 单页左右分栏（左侧提交表单 42%，右侧任务列表 58%），复用后端已有筛选 API，前端自定义 @ 提及浮层

**Tech Stack:** Vue 3 + Element Plus + FastAPI（后端不变）

---

## 文件结构

### 修改文件

| 文件 | 负责内容 |
|------|----------|
| `frontend/src/App.vue` | 全局布局重构为左右分栏，移除路由导航 |
| `frontend/src/views/SubmitTask.vue` | 去掉外层 Card，适配左侧面板，添加 @ 提及浮层 |
| `frontend/src/views/TaskList.vue` | 添加筛选器（状态 Tag + 账号下拉），适配右侧面板 |
| `frontend/src/router/index.js` | 保留路由定义，但根路径直接渲染组合组件 |

### 新增文件

| 文件 | 负责内容 |
|------|----------|
| `frontend/src/views/HomePage.vue` | 新建主页面，组合 SubmitTask 和 TaskList 为左右分栏 |

---

## Task 1: 创建 HomePage 组合组件

**Files:**
- Create: `frontend/src/views/HomePage.vue`

- [ ] **Step 1: 创建 HomePage.vue 文件，搭建左右分栏骨架**

```vue
<!-- frontend/src/views/HomePage.vue -->
<template>
  <div class="home-page">
    <div class="left-panel">
      <SubmitTask />
    </div>
    <div class="right-panel">
      <TaskList />
    </div>
  </div>
</template>

<script setup>
import SubmitTask from './SubmitTask.vue'
import TaskList from './TaskList.vue'
</script>

<style scoped>
.home-page {
  display: flex;
  height: calc(100vh - 60px); /* 减去 header 高度 */
  gap: 0;
}

.left-panel {
  width: 42%;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  padding: 16px;
}

.right-panel {
  width: 58%;
  background: #f5f7fa;
  overflow-y: auto;
  padding: 16px;
}
</style>
```

- [ ] **Step 2: 在浏览器中验证布局显示**

启动前端开发服务器：
```bash
cd frontend && npm run dev
```
打开浏览器访问 `http://localhost:5173`，确认左右分栏比例正确。

- [ ] **Step 3: Commit 骨架文件**

```bash
git add frontend/src/views/HomePage.vue
git commit -m "feat: create HomePage with left-right split layout skeleton"

Confidence: high
Scope-risk: narrow
```

---

## Task 2: 重构 App.vue 为单页布局

**Files:**
- Modify: `frontend/src/App.vue:2-23`（整体 template）
- Modify: `frontend/src/App.vue:25-32`（script）
- Modify: `frontend/src/App.vue:34-46`（style）

- [ ] **Step 1: 重写 App.vue 的 template，改为深色顶栏 + HomePage**

```vue
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
      <HomePage />
    </el-main>
  </el-container>
</template>
```

- [ ] **Step 2: 更新 script，引入 HomePage**

```vue
<script setup>
import { ref, provide } from 'vue'
import AccountSelector from './components/AccountSelector.vue'
import HomePage from './views/HomePage.vue'

const selectedAccountId = ref('')
provide('selectedAccountId', selectedAccountId)
</script>
```

- [ ] **Step 3: 更新 style，添加深色顶栏样式**

```vue
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
```

- [ ] **Step 4: 在浏览器中验证 App.vue 重构效果**

刷新浏览器，确认：
- 顶栏变为深色 `#1e1e2e`
- 左右分栏显示正确
- 账号选择器和"账号管理"按钮位置正确

- [ ] **Step 5: Commit App.vue 重构**

```bash
git add frontend/src/App.vue
git commit -m "refactor: App.vue to dark header + HomePage layout

Constraint: Must keep AccountSelector functional in header
Confidence: high
Scope-risk: narrow"
```

---

## Task 3: 更新路由配置，根路径直接渲染 HomePage

**Files:**
- Modify: `frontend/src/router/index.js:4-12`

- [ ] **Step 1: 修改 router/index.js，将根路径改为 HomePage**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import AccountManager from '../views/AccountManager.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: AccountManager
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

- [ ] **Step 2: 在浏览器中验证路由跳转**

访问 `http://localhost:5173`，确认：
- 根路径直接显示 HomePage（左右分栏）
- 点击顶栏"账号管理"跳转到 `/accounts`
- 从账号管理页面无导航返回主页（需要手动改 URL 或添加返回按钮）

- [ ] **Step 3: Commit 路由重构**

```bash
git add frontend/src/router/index.js
git commit -m "refactor: router to serve HomePage at root path

Confidence: high
Scope-risk: narrow
Directive: AccountManager page still accessible via /accounts route"
```

---

## Task 4: 重构 SubmitTask.vue，去掉外层 Card

**Files:**
- Modify: `frontend/src/views/SubmitTask.vue:3-88`（template）
- Modify: `frontend/src/views/SubmitTask.vue:149-151`（style）

- [ ] **Step 1: 移除 SubmitTask.vue 的 `<el-card>` 外层包装**

将 template 改为：
```vue
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

      <!-- 提示词输入框（后续 Task 5 会添加 @ 功能） -->
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
```

- [ ] **Step 2: 更新 script，添加 upload 处理逻辑**

```vue
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
  // 清空 input 以便重复选择同一文件
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
    // 不跳转到任务列表，因为右侧已经可见
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
```

- [ ] **Step 3: 更新 style，适配左侧面板**

```vue
<style scoped>
.submit-panel {
  /* 去掉 max-width 和 margin，适应左侧面板 */
}

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
```

- [ ] **Step 4: 在浏览器中验证 SubmitTask 重构**

刷新页面，确认：
- 左侧面板无 Card 包装，标题带 `NEW` Tag
- 媒体上传区为三个按钮集中显示
- 上传文件后显示 Tag 预览
- 参数行横向排列
- 提交成功后不跳转，右侧任务列表自动刷新

- [ ] **Step 5: Commit SubmitTask 重构**

```bash
git add frontend/src/views/SubmitTask.vue
git commit -m "refactor: SubmitTask to flat panel without Card wrapper

Constraint: Must fit left panel width 42%
Confidence: high
Scope-risk: narrow"
```

---

## Task 5: TaskList.vue 添加筛选器

**Files:**
- Modify: `frontend/src/views/TaskList.vue:3-8`（template header）
- Modify: `frontend/src/views/TaskList.vue:65-87`（script，添加筛选逻辑）
- Modify: `frontend/src/views/TaskList.vue:122-133`（style）

- [ ] **Step 1: 在 TaskList.vue template 顶部添加筛选器**

```vue
<!-- frontend/src/views/TaskList.vue -->
<template>
  <div class="task-list">
    <div class="list-header">
      <div class="header-title">
        <el-text size="large">任务列表</el-text>
        <el-text size="small" type="info">（共 {{ tasks.length }} 条）</el-text>
      </div>
      <div class="header-actions">
        <!-- 状态筛选：Tag 按钮组 -->
        <el-tag
          v-for="s in statusOptions"
          :key="s.value"
          :type="activeStatus === s.value ? 'primary' : 'info'"
          :effect="activeStatus === s.value ? 'dark' : 'plain'"
          class="filter-tag"
          @click="activeStatus = s.value"
        >
          {{ s.label }}
        </el-tag>
        <!-- 账号筛选：下拉框 -->
        <el-select
          v-model="activeAccount"
          placeholder="账号筛选"
          size="small"
          style="width: 120px; margin-left: 10px"
          clearable
        >
          <el-option label="全部账号" value="" />
          <el-option v-for="acc in accounts" :key="acc.id" :label="acc.id" :value="acc.id" />
        </el-select>
        <el-button :loading="loading" circle size="small" @click="fetchTasks">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 任务卡片列表保持不变 -->
    <el-empty v-if="!tasks.length && !loading" description="暂无任务" />

    <el-card v-for="task in tasks" :key="task.id" class="task-card" shadow="hover">
      <!-- 内容保持不变 -->
    </el-card>
  </div>
</template>
```

- [ ] **Step 2: 更新 script，添加筛选状态和逻辑**

```vue
<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/index.js'
import { Refresh } from '@element-plus/icons-vue'

const tasks = ref([])
const loading = ref(false)
const accounts = ref([])
let refreshTimer = null

// 筛选状态
const activeStatus = ref('')
const activeAccount = ref('')

const statusOptions = [
  { label: '全部', value: '' },
  { label: '等待中', value: 'pending' },
  { label: '生成中', value: 'processing' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' },
]

onMounted(async () => {
  await fetchTasks()
  await fetchAccounts()
  refreshTimer = setInterval(fetchTasks, 10000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})

// 监听筛选条件变化，自动刷新
watch([activeStatus, activeAccount], () => {
  fetchTasks()
})

async function fetchAccounts() {
  try {
    accounts.value = await api.listAccounts()
  } catch (e) {
    ElMessage.error('加载账号失败: ' + e.message)
  }
}

async function fetchTasks() {
  loading.value = true
  try {
    tasks.value = await api.listTasks({
      status: activeStatus.value || undefined,
      account_id: activeAccount.value || undefined,
    })
  } catch (e) {
    ElMessage.error('加载任务失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

// deleteTask 保持不变
async function deleteTask(id) {
  await ElMessageBox.confirm('确认删除该任务记录？', '提示', { type: 'warning' })
  try {
    await api.deleteTask(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

// statusType, statusLabel, formatDate, formatParams 保持不变
</script>
```

- [ ] **Step 3: 更新 style，适配右侧面板和筛选器布局**

```vue
<style scoped>
.task-list {
  /* 去掉 max-width 和 margin，适应右侧面板 */
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.header-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-tag {
  cursor: pointer;
  margin-right: 4px;
}

.task-card {
  margin-bottom: 12px;
  border-left: 3px solid;
}

/* 根据状态设置左侧颜色条 */
.task-card[data-status="success"] { border-left-color: #67c23a; }
.task-card[data-status="processing"] { border-left-color: #e6a23c; }
.task-card[data-status="failed"] { border-left-color: #f56c6c; }
.task-card[data-status="pending"] { border-left-color: #909399; }

.task-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.task-meta {
  flex: 1;
  color: #909399;
  font-size: 13px;
}
.task-params { margin-bottom: 4px; }
.task-prompt { margin: 6px 0; }
.task-result { margin-top: 10px; }
.task-error { margin-top: 8px; }
.task-id { margin-top: 8px; }
</style>
```

- [ ] **Step 4: 在浏览器中验证筛选器功能**

刷新页面，确认：
- 状态 Tag 按钮组显示正确，点击切换状态
- 账号下拉框显示账号列表，选择后筛选生效
- 任务卡片左侧有颜色状态条
- 切换筛选条件后任务列表自动更新

- [ ] **Step 5: Commit TaskList 筛选器**

```bash
git add frontend/src/views/TaskList.vue
git commit -m "feat: add status and account filters to TaskList

Constraint: Reuse backend GET /api/tasks?status=&account_id= params
Confidence: high
Scope-risk: narrow"
```

---

## Task 6: SubmitTask.vue 添加 @ 媒体引用浮层

**Files:**
- Modify: `frontend/src/views/SubmitTask.vue:57-63`（提示词输入框）
- Modify: `frontend/src/views/SubmitTask.vue:91-147`（script，添加 @ 逻辑）

- [ ] **Step 1: 在 SubmitTask.vue 提示词输入框区域添加浮层结构**

```vue
<!-- frontend/src/views/SubmitTask.vue -->
<!-- 替换原提示词 form-item -->
<el-form-item label="提示词">
  <div class="prompt-container">
    <el-input
      ref="promptInput"
      v-model="form.prompt"
      type="textarea"
      :rows="3"
      placeholder="可选：描述生成内容（输入 @ 引用已上传文件）"
      @input="handlePromptInput"
    />
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
          🖼️ 图片{{ i + 1 }} <span class="filename">{{ img.name }}</span>
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
          🎵 音频{{ i + 1 }} <span class="filename">{{ aud.name }}</span>
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
          🎬 视频{{ i + 1 }} <span class="filename">{{ vid.name }}</span>
        </div>
      </div>
    </div>
  </div>
</el-form-item>
```

- [ ] **Step 2: 在 script 中添加 @ 浮层逻辑**

```vue
<script setup>
// ... 原有 imports

const promptInput = ref(null)
const showMentionPopup = ref(false)

function handlePromptInput(value) {
  // 检测最后输入字符是否为 @
  const lastChar = value.slice(-1)
  if (lastChar === '@') {
    // 只在有已上传文件时弹出
    if (form.value.images.length || form.value.audios.length || form.value.videos.length) {
      showMentionPopup.value = true
    }
  } else {
    showMentionPopup.value = false
  }
}

function insertMention(type, index) {
  const mention = `@${type}${index}`
  const textarea = promptInput.value?.textarea
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    // 替换最后的 @ 为 @图片1 等
    const before = form.value.prompt.slice(0, start - 1) // 移除最后的 @
    const after = form.value.prompt.slice(end)
    form.value.prompt = before + mention + ' ' + after
  } else {
    // fallback：直接替换最后的 @
    form.value.prompt = form.value.prompt.slice(0, -1) + mention + ' '
  }
  showMentionPopup.value = false
}
</script>
```

- [ ] **Step 3: 在 style 中添加浮层样式**

```vue
<style scoped>
/* ... 原有样式 */

.prompt-container {
  position: relative;
}

.mention-popup {
  position: absolute;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 6px;
  z-index: 10;
  max-height: 200px;
  overflow-y: auto;
  width: 200px;
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
  padding: 2px 6px;
}

.mention-item {
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 3px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.mention-item:hover {
  background: #ecf5ff;
}

.filename {
  color: #909399;
  font-size: 10px;
}
</style>
```

- [ ] **Step 4: 在浏览器中验证 @ 浮层功能**

刷新页面，测试：
- 上传至少一个图片或音频
- 在提示词框输入 `@`，确认浮层弹出
- 点击浮层中的文件，确认插入 `@图片1` 等标记
- 继续输入其他内容，确认标记后有空格
- 无上传文件时输入 `@`，确认不弹出浮层

- [ ] **Step 5: Commit @ 提及功能**

```bash
git add frontend/src/views/SubmitTask.vue
git commit -m "feat: add @ media mention popup in prompt input

Constraint: Only show popup when files uploaded
Confidence: high
Scope-risk: narrow
Directive: @标记为纯文本，后端不做解析"
```

---

## Task 7: 整体测试和验证

**Files:**
- 无文件修改，整体验证

- [ ] **Step 1: 启动完整应用，验证所有功能**

```bash
cd frontend && npm run dev
```

浏览器测试清单：
1. 左右分栏比例 42%/58% 正确
2. 深色顶栏显示正常
3. 左侧表单上传文件、提交任务正常
4. 右侧任务列表自动刷新、筛选器切换生效
5. 提示词 `@` 浮层弹出、选择、插入正常
6. 提交任务后右侧列表立即显示新任务

- [ ] **Step 2: 检查是否有遗留的导航菜单元素**

确认 App.vue 中无 `<el-menu>` 导航菜单，任务列表和提交任务不再作为独立路由页面。

- [ ] **Step 3: Commit 最终验证完成标记**

```bash
git add docs/superpowers/specs/2026-04-07-ui-optimization-round2-design.md
git commit -m "chore: mark design spec as verified after implementation

Confidence: high
Scope-risk: narrow"
```

---

## 实施完成后的清理

所有任务完成后：
1. 停止前端开发服务器（Ctrl+C）
2. 确认无未提交的文件（`git status`）
3. 最终提交日志应包含 7 个有意义的 commit

---

## Self-Review Checklist

**Spec coverage:**
- ✅ 整体布局重构 → Task 1, 2, 3
- ✅ 任务列表筛选 → Task 5
- ✅ 提示词 @ 引用 → Task 6
- ✅ 无后端改动 → 全部前端任务
- ✅ 保留账号管理路由 → Task 3

**Placeholder scan:**
- ✅ 无 TBD/TODO
- ✅ 所有代码步骤包含完整代码块
- ✅ 所有测试步骤包含具体验证点

**Type consistency:**
- ✅ `form.images/audios/videos` 数组结构一致
- ✅ `activeStatus/activeAccount` ref 类型一致
- ✅ `api.listTasks` 参数名与后端匹配