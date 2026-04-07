# Dreamina CLI Manager

一个基于 Web 的 Dreamina 多模态视频生成管理工具。

## 功能特性

- **账号管理**：新增、删除、登录、退出登录
- **任务提交**：上传图片/音频/视频，配置生成参数
- **任务跟踪**：自动轮询任务状态，展示视频链接
- **积分查询**：实时查询账号积分余额

## 技术栈

- **前端**：Vue 3 + Vite + Element Plus
- **后端**：FastAPI + APScheduler + SQLite
- **部署**：Docker Compose

## 快速开始

```bash
# 克隆项目
git clone git@github.com:jrient/dreamina-cli-manager.git
cd dreamina-cli-manager

# 启动服务
docker compose up -d

# 访问
open http://localhost:8090
```

## 使用说明

### 1. 新增账号

1. 进入「账号管理」页面
2. 点击「新增账号」，输入账号 ID
3. 点击「登录」按钮
4. 在浏览器中打开「获取凭证 JSON」链接（需先登录即梦账号）
5. 复制页面显示的 JSON 内容
6. 粘贴到输入框，点击「导入凭证」

### 2. 提交任务

1. 在顶部选择已登录的账号
2. 进入「提交任务」页面
3. 上传图片/音频/视频文件
4. 配置参数（时长、比例、模型版本）
5. 点击「提交任务」

### 3. 查看任务

- 任务列表每 10 秒自动刷新
- 完成后显示视频链接，可点击下载

## 文件限制

- 图片：最多 9 张
- 视频：最多 3 个
- 音频：最多 3 个，时长 2-15 秒
- 比例：1:1, 3:4, 16:9, 4:3, 9:16, 21:9
- 时长：4-15 秒

## 目录结构

```
.
├── backend/           # FastAPI 后端
│   ├── main.py
│   ├── routers/
│   ├── services/
│   └── Dockerfile
├── frontend/          # Vue 3 前端
│   ├── src/
│   ├── nginx.conf
│   └── Dockerfile
├── db/                # SQLite 数据库
├── uploads/           # 上传文件
└── docker-compose.yml
```

## TODO

- [ ] 解决服务器上传带宽不足导致大文件上传超时问题
  - 当前上传带宽约 60-160 KB/s，大文件（>1MB）可能超时
  - 可能方案：前端添加文件大小检查、优化服务器带宽、尝试直连 CDN 节点

## License

MIT