# 任务队列设计：处理即梦并发限制

## 问题背景

即梦 API 在单账号并发任务超过 10 个时返回错误：
```
ret=1310, message=ExceedConcurrencyLimit
```

当前行为：直接报 HTTP 502，任务失败，文件删除，无重试机制。

## 目标

实现任务队列：当触发并发限制时，任务进入排队状态，等待前面的任务完成后自动提交。

## 设计概览

- 新增 `queued` 状态：任务已创建、文件已保存，等待提交
- 每账号最多 10 个活跃任务（pending + processing）
- 队列调度器在 poller 中运行，每 10 秒检查并提交 queued 任务

## 详细设计

### 1. 数据库 Schema 变更

当前 `tasks` 表以 `submit_id` 作为主键 `id`，需解耦：

```sql
-- 新增列（迁移时添加）
ALTER TABLE tasks ADD COLUMN submit_id TEXT;  -- 提交成功后填入，queued 时为 NULL
```

**id 生成策略**：
- 新任务使用 UUID（`uuid.uuid4().hex[:12]`）
- 文件存储路径：`uploads/<id>/`（不再依赖 submit_id 重命名）

**params JSON 新增字段**：
```json
{
  "duration": 5,
  "ratio": "16:9",
  "model_version": "seedance2.0fast",
  "image_paths": ["uploads/<id>/img1.jpg"],
  "video_paths": [],
  "audio_paths": []
}
```

### 2. 新增异常类

`backend/services/dreamina.py`：

```python
class ConcurrencyLimitError(Exception):
    """即梦并发限制，任务需排队等待"""
    pass
```

在 `submit_multimodal2video` 中识别限流错误：
- 当 `fail_reason` 包含 `ExceedConcurrencyLimit` 或 `ret=1310` 时，抛出 `ConcurrencyLimitError`
- 其他错误继续抛出 `RuntimeError`

### 3. API 行为变更

`POST /api/tasks`：
- 提交成功 → 201，`status: "pending"`，`submit_id` 有值
- 遇 `ConcurrencyLimitError` → **201，`status: "queued"`，`submit_id: null`**
- 其他错误 → 502

`GET /api/tasks` 返回 queued 任务，前端显示"排队中"。

### 4. 队列调度器

`backend/services/poller.py` 新增 `dispatch_queued_tasks`：

```python
async def dispatch_queued_tasks():
    """检查并提交 queued 任务"""
    # 1. 查询所有 queued 任务，按账号分组
    # 2. 对每个账号：
    #    - 统计 pending + processing 数量
    #    - 若 < 10：取最早的 queued 任务尝试提交
    #    - 提交成功：更新 submit_id，状态改 pending
    #    - 提交限流：跳过（说明其他账号刚提交了）
    #    - 提交失败：状态改 failed
    # 3. 重复直到无 queued 或所有账号满 10
```

调度时机：复用现有 `POLL_INTERVAL`，在 `poll_tasks` 之后调用。

### 5. 状态流转

```
创建任务 → queued（遇限流）或 pending（提交成功）
queued → pending（调度器提交成功）
pending → processing → success/failed（poller 更新）
```

### 6. 前端适配

`TaskList.vue` 新增状态显示：
- `queued` → "排队中"（灰色图标）
- `pending` → "等待开始"
- `processing` → "生成中"

## 实现步骤

1. 数据库迁移：新增 `submit_id` 列，修改 `database.py`
2. `dreamina.py`：新增 `ConcurrencyLimitError`，识别限流错误
3. `tasks.py`：创建任务时用 UUID，遇限流存 queued 状态
4. `poller.py`：新增 `dispatch_queued_tasks`
5. `main.py`：调度器加入 lifespan
6. 前端：新增 queued 状态显示

## 风险与边界

- **重启不丢队列**：queued 任务文件路径存于 params，重启后可恢复
- **文件清理**：任务失败或删除时，清理 `uploads/<id>/`
- **旧数据兼容**：迁移时将现有 `id` 复制到 `submit_id`