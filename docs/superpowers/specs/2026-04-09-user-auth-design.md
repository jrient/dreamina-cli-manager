# 用户认证与权限系统设计

## 背景

当前系统无用户体系，所有 API 公开访问。需要引入用户认证和权限管理，实现多团队数据隔离。

## 目标

- 多团队隔离：不同团队各自管理项目和账号
- 简单认证：用户名密码登录，Session 方式
- 精细权限：账号按项目、按用户分配
- 分集功能：项目级别任务分集管理

## 角色体系

| 角色 | 获取方式 | 权限范围 |
|------|----------|----------|
| **系统管理员** | 第一个注册用户自动成为管理员；之后由管理员指定 | 所有项目、所有用户、所有账号 |
| **项目拥有者** | 创建项目时自动成为该项目拥有者 | 自己的项目：全部管理权限 |
| **协作者** | 由拥有者/管理员在项目管理界面添加 | 指定项目：创建任务、查看自己的任务 |

### 权限矩阵

| 操作 | 管理员 | 项目拥有者 | 协作者 |
|------|:------:|:----------:|:------:|
| 创建/删除用户 | ✓ | - | - |
| 重置用户密码 | ✓ | - | - |
| 查看所有项目 | ✓ | - | - |
| 创建项目 | ✓ | ✓ | - |
| 删除项目 | ✓ | ✓ | - |
| 添加/移除协作者 | ✓ | ✓ | - |
| 配置项目账号池 | ✓ | ✓ | - |
| 分配协作者账号 | ✓ | ✓ | - |
| 配置项目集数 | ✓ | ✓ | - |
| 创建任务 | ✓ | ✓ | ✓ |
| 查看/删除自己的任务 | ✓ | ✓ | ✓ |
| 查看项目所有任务 | ✓ | ✓ | - |

---

## 数据模型

### 新增表

#### users 表
```sql
CREATE TABLE users (
    id          TEXT PRIMARY KEY,      -- UUID[:12]
    username    TEXT UNIQUE NOT NULL,  -- 中文用户名
    password    TEXT NOT NULL,         -- bcrypt 哈希
    is_admin    INTEGER DEFAULT 0,     -- 是否管理员
    deleted_at  TEXT,                  -- 软删除时间
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
```

#### project_members 表
```sql
CREATE TABLE project_members (
    project_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL,         -- 'owner' / 'collaborator'
    created_at  TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### project_accounts 表（项目账号池）
```sql
CREATE TABLE project_accounts (
    project_id  TEXT NOT NULL,
    account_id  TEXT NOT NULL,         -- 即梦账号ID
    PRIMARY KEY (project_id, account_id)
);
```

#### member_accounts 表（协作者账号分配）
```sql
CREATE TABLE member_accounts (
    project_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    account_id  TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id, account_id),
    FOREIGN KEY (project_id, account_id) REFERENCES project_accounts(project_id, account_id)
);
```

### 现有表修改

#### projects 表新增字段
```sql
ALTER TABLE projects ADD COLUMN episode_count INTEGER DEFAULT 50;  -- 集数配置
ALTER TABLE projects ADD COLUMN creator_id TEXT;                    -- 创建者用户ID
```

#### tasks 表新增字段
```sql
ALTER TABLE tasks ADD COLUMN creator_id TEXT;   -- 创建任务的用户ID
ALTER TABLE tasks ADD COLUMN episode INTEGER;   -- 分集号
```

---

## 认证流程

### 登录
1. 用户提交 username + password
2. 后端验证 bcrypt 哈希
3. 创建 Session，存用户 ID
4. 返回用户信息

### Session 存储
- 服务端内存存储
- 可选持久化到 SQLite（sessions 表）

### 权限检查
- 每个请求通过中间件检查 Session
- 获取用户角色信息
- 在路由层做权限过滤

### 登出
- 清除 Session

---

## API 设计

### 认证接口
```
POST /api/auth/login          # 登录
POST /api/auth/logout         # 登出
GET  /api/auth/me             # 获取当前用户信息
```

### 用户管理（管理员）
```
GET    /api/users             # 用户列表
POST   /api/users             # 创建用户
PUT    /api/users/{id}        # 更新用户（重置密码、设置管理员）
DELETE /api/users/{id}        # 软删除用户
```

### 项目管理（权限调整）
```
GET  /api/projects                    # 返回用户可见的项目
POST /api/projects                    # 创建项目（自动成为拥有者）
GET  /api/projects/{id}/members       # 项目成员列表
POST /api/projects/{id}/members       # 添加协作者
DELETE /api/projects/{id}/members/{uid}  # 移除协作者
PUT  /api/projects/{id}/accounts      # 配置项目账号池（下拉多选）
GET  /api/projects/{id}/member-accounts   # 获取成员账号分配
PUT  /api/projects/{id}/member-accounts/{uid}  # 配置协作者可用账号
PUT  /api/projects/{id}/settings      # 配置集数等
```

### 任务 API（权限过滤）
```
GET  /api/tasks            # 自动过滤：管理员看全部，协作者只看自己的
POST /api/tasks            # 创建任务需要验证用户对该账号有权限
```

---

## 前端设计

### 新增页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录页 | `/login` | 用户名密码登录 |
| 用户管理 | `/admin/users` | 管理员查看/创建/删除用户、重置密码、设置管理员 |

### 现有页面调整

| 页面 | 调整内容 |
|------|----------|
| 项目列表 | 只显示用户参与的项目（管理员显示全部） |
| 项目管理页 | Tab：任务、素材、设置 |
| 任务提交 | 账号下拉框只显示用户可用账号；新增分集下拉框（1到集数上限） |
| 任务列表 | 新增列：创建者、分集；筛选框增加分集筛选 |

### 项目管理页设置 Tab 结构

```
项目设置
├── 集数配置（下拉选择，任务分集范围 1-N）
├── 项目账号池（下拉多选框）
└── 协作者管理
    ├── 添加协作者
    └── 协作者列表（用户名、可用账号、操作）
        └── 配置弹窗：勾选项目账号池中的账号
```

---

## 错误处理

### 认证相关

| 场景 | 处理方式 |
|------|----------|
| 用户名已存在 | 400："用户名已存在" |
| 登录失败（密码错误） | 401："用户名或密码错误" |
| 未登录访问受保护 API | 401，前端重定向到登录页 |
| 无权限访问资源 | 403："无权限访问此项目/任务" |
| Session 过期 | 401，前端提示"登录已过期"并重定向 |

### 项目权限相关

| 场景 | 处理方式 |
|------|----------|
| 协作者使用未授权账号提交任务 | 403："您无权限使用该账号" |
| 删除有任务的项目 | 软删除，保留数据 |
| 删除用户时该用户有任务 | 禁止删除，提示"该用户仍有任务记录" |
| 项目账号池为空 | 允许，但任务提交时提示"项目未配置可用账号" |
| 协作者账号分配为空 | 允许，但该协作者无法提交任务 |

### 用户软删除

| 场景 | 处理方式 |
|------|----------|
| 删除用户 | 软删除，设置 deleted_at |
| 已删除用户登录 | 401："账户已被禁用" |
| 已删除用户名重新注册 | 400："用户名已存在" |
| 用户列表 | 默认不显示已删除用户，管理员可切换显示 |
| 项目成员列表 | 已删除用户显示"用户已删除"，可移除 |

---

## 实现顺序

1. 数据库表创建与迁移
2. 用户认证 API（login/logout/me）
3. 用户管理 API（管理员）
4. 权限中间件
5. 项目权限 API（成员、账号、设置）
6. 任务 API 权限过滤
7. 前端登录页
8. 前端用户管理页
9. 前端项目设置 Tab
10. 前端任务分集功能