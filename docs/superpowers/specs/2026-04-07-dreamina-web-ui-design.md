# Dreamina Multimodal2Video Web UI — 设计规格

**日期：** 2026-04-07
**状态：** 已实现
**更新日期：** 2026-04-07（功能验证完成）

---

## 1. 项目概述

构建一个 Web 界面，让用户通过浏览器操作 `dreamina multimodal2video` CLI 命令。核心功能包括：

- 账号管理（新增、删除、登录、退出登录）
- 上传图片、音频、视频等多模态输入
- 提交异步生成任务并自动跟踪状态
- 展示完成后的视频链接供下载

**不在范围内：** Web 端用户登录/认证、负载均衡、自动账号轮换。

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Network: dreamina-net                               │
│                                                             │
│  ┌──────────────┐    ┌───────────────────────────────────┐  │
│  │  frontend    │    │    backend                        │  │
│  │  Nginx :8090 │───▶│    FastAPI :8000                  │  │
│  │  Vue 3       │    │                                   │  │
│  │  Element Plus│    │  ┌─────────────────────────────┐  │  │
│  └──────────────┘    │  │ APScheduler (轮询服务)      │  │  │
│                      │  └─────────────────────────────┘  │  │
│                      │                                   │  │
│                      │  SQLite DB (/app/db/tasks.db)     │  │
│                      │                                   │  │
│                      │  账号存储:                        │  │
│                      │  /root/.dreamina_accounts/<id>/   │  │
│                      │    └─ .dreamina_cli/              │  │
│                      │       └─ credential.json          │  │
│                      └───────────────────────────────────┘  │
│                                                             │
│  Volumes (代码挂载，实时更新):                               │
│  - ./backend/ → /app (代码)                                 │
│  - ./frontend/src/ → /app/src (源码)                       │
│  - ./db/ → /app/db (数据库)                                 │
│  - ./uploads/ → /app/uploads (临时文件)                     │
└─────────────────────────────────────────────────────────────┘
```

- **Nginx** serve Vue 3 静态文件，端口 8090，`/api/` 反向代理到 FastAPI
- **FastAPI** 处理所有 API 请求，通过调用 `dreamina` CLI 执行任务
- **APScheduler** 每 10 秒扫描 pending/processing 任务，调用 `dreamina query_result` 更新状态
- **账号隔离**：每个账号独立 `HOME` 目录 (`/root/.dreamina_accounts/<account_id>/`)

---

## 3. 后端设计

### 3.1 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- APScheduler（后台定时任务）
- SQLite（通过 `aiosqlite` 异步访问）
- `python-multipart`（文件上传）

### 3.2 账号管理（已实现）

**账号存储结构：**
```
/root/.dreamina_accounts/
├── jrient/
│   └── .dreamina_cli/
│       └── credential.json   # 登录凭证
├── jrient2/
│   └── .dreamina_cli/
│       └── credential.json
└── test-account/
    └── .dreamina_cli/
        └── credential.json
```

**账号隔离机制：**
- 每个账号设置独立的 `HOME` 环境变量
- 调用 `dreamina` CLI 时：`HOME=/root/.dreamina_accounts/<account_id>`
- 凭证文件存储在 `~/.dreamina_cli/credential.json`

### 3.3 API 路由（已实现）

```
# 账号管理
GET  /api/accounts
     返回账号列表（id, logged_in, credit）

POST /api/accounts
     新增账号（body: {account_id: string})

DELETE /api/accounts/{id}
     删除账号及其凭证目录

POST /api/accounts/{id}/start-login
     启动登录流程，返回 random_secret_key 和 json_url

POST /api/accounts/{id}/import-credentials
     导入凭证 JSON（body: {credentials_json: string})

POST /api/accounts/{id}/logout
     退出登录（删除 credential.json）

GET  /api/accounts/{id}/credit
     查询账号积分

POST /api/accounts/{id}/refresh-credit
     刷新账号积分

# 任务管理
POST /api/tasks
     提交 multimodal2video 任务
     Content-Type: multipart/form-data
     字段：
       account_id   str       必填，选择的账号 ID
       images[]     file[]    图片文件，最多 9 个
       audios[]     file[]    音频文件，最多 3 个
       videos[]     file[]    视频文件，最多 3 个
       prompt       str       可选，生成提示词
       duration     int       视频时长（4-15），默认 5
       ratio        str       比例
       model_version str      模型版本

GET  /api/tasks
     列出所有任务

GET  /api/tasks/{id}
     查询单个任务详情

DELETE /api/tasks/{id}
     删除任务记录

# 健康检查
GET  /api/health
     返回 {status: "ok"}
```

---

## 4. 前端设计

### 4.1 技术栈

- Vue 3 + Vite
- Element Plus（UI 组件库）
- Vue Router（路由）
- 纯 fetch API 与后端通信

### 4.2 页面结构（已实现）

```
App.vue
├── Header（顶部导航）
│   ├── 标题：Dreamina 视频生成
│   ├── AccountSelector（账号选择器 + 余额查询）
│   └── 菜单：提交任务 / 任务列表 / 账号管理
│
├── 视图一：/ 提交任务（SubmitTask.vue）
│   ├── 文件上传区（图片、音频、视频）
│   ├── 参数配置（Prompt、时长、比例、模型）
│   └── 提交按钮
│
├── 视图二：/tasks 任务列表（TaskList.vue）
│   └── 任务卡片列表（状态、账号、参数、视频链接）
│
└── 视图三：/accounts 账号管理（AccountManager.vue）
    ├── 账号列表表格
    │   ├── 账号 ID
    │   ├── 登录状态（已登录/未登录）
    │   ├── 积分余额（数字显示 total_credit）
    │   └── 操作按钮（登录/刷新积分/退出登录/删除）
    ├── 新增账号对话框
    └── 登录流程对话框
        ├── 步骤说明
        ├── 登录链接 + 获取凭证 JSON 链接
        └── JSON 输入框 + 导入按钮
```

### 4.3 登录流程（已实现）

```
用户点击「登录」按钮
    ↓
调用 POST /api/accounts/{id}/start-login
    ↓
后端执行 timeout 3 dreamina login --debug
    ↓
提取 random_secret_key，返回 json_url
    ↓
用户在浏览器打开 json_url（需先登录即梦账号）
    ↓
复制页面显示的 JSON 内容
    ↓
粘贴到输入框，点击「导入凭证」
    ↓
调用 POST /api/accounts/{id}/import-credentials
    ↓
后端执行 dreamina import_login_response --file
    ↓
验证成功，显示积分，登录完成
```

### 4.4 自动刷新

- 任务列表页每 **10 秒** 自动刷新
- 账号积分可手动点击「刷新积分」查询

---

## 5. 功能验证清单

| 功能 | 状态 | 验证方式 |
|------|------|---------|
| 新增账号 | ✅ 已验证 | POST /api/accounts，账号目录创建 |
| 删除账号 | ✅ 已验证 | DELETE /api/accounts/{id}，目录删除 |
| 登录流程 | ✅ 已验证 | start-login → import-credentials 完整流程 |
| 退出登录 | ✅ 已验证 | POST /api/accounts/{id}/logout |
| 积分查询 | ✅ 已验证 | GET /api/accounts/{id}/credit |
| 积分显示优化 | ✅ 已验证 | JSON 解析显示 total_credit |
| 账号选择器 | ✅ 已验证 | Header 组件，provide/inject 跨组件通信 |
| 提交任务 | ✅ 已验证 | POST /api/tasks，文件上传，返回 submit_id |
| 任务列表 | ✅ 已验证 | GET /api/tasks，10 秒自动刷新 |
| 任务状态轮询 | ✅ 已验证 | APScheduler 每 10 秒查询 gen_status |
| 视频链接展示 | ✅ 已验证 | 任务卡片显示 result_url |
| 错误即时反馈 | ✅ 已验证 | --poll=1 参数，提交失败立即返回错误 |
| 代码热更新 | ✅ 已验证 | Docker volumes 挂载 |
| 端口占用处理 | ✅ 已验证 | 启动登录前 pkill dreamina |
| 文件上传限制 | ✅ 已验证 | nginx client_max_body_size 500m |

---

## 6. 已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 异步任务状态不同步 | 即梦服务器对无 poll 的任务不返回失败状态 | 添加 `--poll=1` 参数，提交时立即获取初始状态 |
| 音频时长超限 | 用户上传 47 秒音频，超出 2-15 秒限制 | 由即梦 CLI 校验，错误立即返回给用户 |
| 外层网关限制 | 用户通过 nginx gateway 访问，有 body 大小限制 | 需在 nginx gateway 配置 `client_max_body_size 500m` |

---

## 6. Docker 部署

### 6.1 docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    volumes:
      - ./backend:/app          # 代码挂载
      - ./db:/app/db
      - ./uploads:/app/uploads
    networks:
      - dreamina-net
    ports:
      - "8000:8000"             # 可选，直接访问 API

  frontend:
    build: ./frontend
    volumes:
      - ./frontend/src:/app/src  # 源码挂载
    ports:
      - "8090:80"
    depends_on:
      - backend
    networks:
      - dreamina-net
```

### 6.2 启动命令

```bash
docker compose up -d
# 访问 http://localhost:8090
```

---

## 7. 关键约束

- `multimodal2video` 至少需要一个 `--image` 或 `--video`
- 音频文件需 2-15 秒（由 dreamina CLI 校验）
- 输入限制：image ≤ 9，video ≤ 3，audio ≤ 3
- 支持的比例：1:1, 3:4, 16:9, 4:3, 9:16, 21:9
- 视频分辨率固定 720p
- 时长范围：4-15 秒
- 端口 8090（外层 nginx gateway 需单独配置 client_max_body_size）