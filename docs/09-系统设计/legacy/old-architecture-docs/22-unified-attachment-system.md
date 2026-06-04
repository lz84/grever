# 统一附件体系设计文档

**日期**：2026-05-20  
**作者**：刚子  
**状态**：设计阶段，待评审

---

## 1. 现状

### 1.1 当前问题

| 问题 | 说明 |
|------|------|
| 单实体绑定 | `task_attachments` 表只有 `task_id`，附件只能挂到 task |
| 重复存储 | 同一文件被多个实体使用时无法复用 |
| 零 API | 附件表存在但没有上传/下载/删除 API |
| 前端缺失 | 创建目标、任务等页面没有附件上传入口 |
| 无鉴权 | 文件路径直接暴露，无下载鉴权 |
| 无约束 | 没有大小限制、类型限制，可上传任意文件 |

### 1.2 现有表结构（将被废弃）

```sql
-- 旧表，待迁移后删除
CREATE TABLE task_attachments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER,
    uploaded_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. 目标

1. **一套体系服务所有实体**：Goal / Project / Task / Scenario / Step / Agent 等
2. **文件去重**：同一文件 hash 相同只存一份物理文件
3. **安全可控**：大小限制 + 类型黑名单 + 下载鉴权
4. **路径统一**：`{根目录}/{year}/{month}/{id}_{filename}`
5. **向后兼容**：迁移旧 `task_attachments` 数据，不丢失

---

## 3. 数据模型

### 3.1 ER 图

```
┌─────────────────────┐          ┌─────────────────────┐
│   attachments       │          │   attachment_links  │
├─────────────────────┤          ├─────────────────────┤
│ id          TEXT PK │◄─────────│ id          TEXT PK │
│ filename    TEXT    │          │ attachment_id FK    │
│ file_path   TEXT    │          │ entity_type  TEXT   │
│ mime_type   TEXT    │          │ entity_id    TEXT   │
│ sha256_hash TEXT    │          │ created_by   TEXT   │
│ file_size   INTEGER │          │ created_at   TS     │
│ created_by  TEXT    │          └─────────────────────┘
│ created_at  TS      │                    │
└─────────────────────┘                    ▼
                                  ┌─────────────────────┐
                                  │  支持 entity_type    │
                                  │  goal/project/task  │
                                  │  scenario/step/...  │
                                  └─────────────────────┘
```

### 3.2 attachments 表

| 列 | 类型 | 约束 | 说明 |
|---|------|------|------|
| id | TEXT | PK | UUID32（如 `att-xxxxxxx`） |
| filename | TEXT | NOT NULL | 原始文件名 |
| file_path | TEXT | NOT NULL | 服务器物理路径（绝对路径或相对于根目录） |
| mime_type | TEXT | | MIME 类型 |
| sha256_hash | TEXT | **NOT NULL, UNIQUE** | 文件 SHA256，用于去重 |
| file_size | INTEGER | | 字节数 |
| created_by | TEXT | | 上传者 ID |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

### 3.3 attachment_links 表

| 列 | 类型 | 约束 | 说明 |
|---|------|------|------|
| id | TEXT | PK | UUID32 |
| attachment_id | TEXT | FK → attachments.id, NOT NULL | |
| entity_type | TEXT | NOT NULL | 实体类型：`goal`/`project`/`task`/`scenario`/`step`/`agent` |
| entity_id | TEXT | NOT NULL | 实体 UUID |
| created_by | TEXT | | 关联创建者 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

### 3.4 索引

```sql
-- 按实体查附件（最高频查询）
CREATE INDEX idx_attachment_links_entity ON attachment_links(entity_type, entity_id);

-- 按附件查关联
CREATE INDEX idx_attachment_links_attachment ON attachment_links(attachment_id);

-- 按 hash 去重查询
CREATE INDEX idx_attachments_hash ON attachments(sha256_hash);
```

### 3.5 迁移脚本

```sql
-- 1. 创建新表
CREATE TABLE attachments (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT,
    sha256_hash TEXT NOT NULL UNIQUE,
    file_size INTEGER,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE attachment_links (
    id TEXT PRIMARY KEY,
    attachment_id TEXT NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attachment_links_entity ON attachment_links(entity_type, entity_id);
CREATE INDEX idx_attachment_links_attachment ON attachment_links(attachment_id);
CREATE INDEX idx_attachments_hash ON attachments(sha256_hash);

-- 2. 迁移旧数据（Python 脚本执行）
--    对每个 task_attachments 记录：
--    a. 计算文件 sha256
--    b. 如果该 hash 已存在 → 复用 attachment，只建新 link
--    c. 如果文件不存在 → 标记 migrated=false，跳过
--    d. 文件存在且 hash 唯一 → 复制到新路径，建 attachment + link

-- 3. 验证无误后删除旧表
DROP TABLE task_attachments;
```

---

## 4. API 设计

### 4.1 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/attachments/upload` | 上传附件 |
| POST | `/api/v1/attachments/{id}/link` | 关联附件到实体 |
| GET | `/api/v1/attachments/{id}/download` | 下载附件 |
| DELETE | `/api/v1/attachments/{id}` | 删除附件（物理删除） |
| DELETE | `/api/v1/attachments/{id}/link/{entity_type}/{entity_id}` | 取消关联 |
| GET | `/api/v1/attachments` | 查询实体的附件列表 |
| HEAD | `/api/v1/attachments/{id}` | 获取附件元信息 |

### 4.2 上传附件

```
POST /api/v1/attachments/upload
Content-Type: multipart/form-data

Body:
  file:        <binary>        # 必填
  entity_type: string          # 必填，如 "goal"
  entity_id:   string          # 必填，如 "goal-xxxxxx"
  created_by:  string (可选)   # 默认从鉴权信息提取
```

**上传流程**：
1. 校验文件大小（≤ 50MB）
2. 校验文件扩展名（检查黑名单）
3. 计算 sha256_hash
4. 查询是否已存在相同 hash：
   - **存在** → 复用该 attachment，只创建新 link
   - **不存在** → 生成新 id，保存文件到新路径，创建 attachment + link
5. 返回 `{ "attachment_id": "...", "reused": true/false }`

**响应**：
```json
{
    "success": true,
    "attachment_id": "att-abc123",
    "reused": false,
    "filename": "需求文档.pdf",
    "file_size": 1048576,
    "mime_type": "application/pdf"
}
```

**错误码**：

| 错误 | HTTP | 说明 |
|------|------|------|
| FILE_TOO_LARGE | 413 | 超过 50MB |
| FILE_TYPE_BLOCKED | 400 | 扩展名在黑名单 |
| MISSING_FILE | 400 | 未传文件 |
| INVALID_ENTITY | 400 | entity_type 不合法 |
| ENTITY_NOT_FOUND | 404 | entity_id 不存在 |

### 4.3 关联附件到实体

```
POST /api/v1/attachments/{id}/link
Body: { "entity_type": "project", "entity_id": "proj-xxxxx" }
```

用于把已有附件关联到另一个实体（不需要重新上传）。

### 4.4 下载附件

```
GET /api/v1/attachments/{id}/download
GET /api/v1/attachments/{id}/download?download=1  # 强制下载（Content-Disposition: attachment）
```

走后端流式返回，支持鉴权。

### 4.5 删除附件

```
DELETE /api/v1/attachments/{id}
```

- 删除所有 link 记录
- 删除物理文件
- 删除 attachment 记录
- ⚠️ 如果有其他 entity 关联此附件，返回 409 CONFLICT，需先取消所有 link

或者提供 `?force=true` 参数：强制删除所有关联和物理文件（危险操作，需鉴权）。

### 4.6 取消关联

```
DELETE /api/v1/attachments/{id}/link/{entity_type}/{entity_id}
```

- 只删除 link，不删除 attachment，不删除物理文件

### 4.7 查询实体附件列表

```
GET /api/v1/attachments?entity_type=goal&entity_id=goal-xxxxx
```

**响应**：
```json
{
    "attachments": [
        {
            "id": "att-abc123",
            "filename": "需求文档.pdf",
            "mime_type": "application/pdf",
            "file_size": 1048576,
            "sha256_hash": "a1b2c3...",
            "created_at": "2026-05-20T12:00:00Z",
            "created_by": "user-xxx"
        }
    ],
    "total": 1
}
```

---

## 5. 安全设计

### 5.1 文件大小限制

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ATTACHMENT_MAX_SIZE` | 50MB (52428800 bytes) | 单文件最大尺寸 |

在 FastAPI 的 `UploadFile` 层和 Nginx 层都要配置。

### 5.2 文件类型限制（黑名单制）

```python
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.scr', '.msi',
    '.js', '.vbs', '.ps1', '.wsf', '.hta',
    '.dll', '.sys', '.com', '.pif', '.lnk',
    '.jar', '.app', '.sh', '.bash',
}
```

白名单制可以后续加（比如只在特定场景下限制为文档类型）。

### 5.3 文件名安全

- 原始文件名存入 `filename` 字段（用于下载时返回）
- 存储时使用 `{id}_{原文件名}` 避免冲突
- 禁止文件名中包含 `..`（防止路径穿越）

### 5.4 存储路径规范

```
{ATTACHMENT_ROOT}/{year}/{month}/{id}_{original_filename}
```

示例：
```
/data/attachments/2026/05/att-abc123_需求文档.pdf
```

- `year` = 上传日期的年（如 `2026`）
- `month` = 上传日期的月（如 `05`）
- 目录不存在时自动创建
- `ATTACHMENT_ROOT` 从 `.env` 读取，默认 `data/attachments`

### 5.5 下载鉴权

所有下载请求必须经过后端 API：
1. 验证请求者有权限访问该附件关联的实体
2. 流式返回文件内容
3. 记录下载审计日志（可选）

---

## 6. 前端集成

### 6.1 CreateGoal 页面

在表单底部（提交按钮上方）增加附件上传区：

```
┌─────────────────────────────────────────┐
│  附件 (可选)                             │
│  ┌───────────────────────────────────┐  │
│  │  📎 拖拽文件到此处，或点击选择      │  │
│  │                                   │  │
│  │  最大 50MB，不允许可执行文件        │  │
│  └───────────────────────────────────┘  │
│                                         │
│  📄 需求文档.pdf       1.2 MB     ✕     │
│  📊 原型图.png         3.4 MB     ✕     │
└─────────────────────────────────────────┘
```

**交互**：
- 支持拖拽上传 + 点击选择
- 上传中显示进度条
- 上传成功显示文件名 + 大小 + 删除按钮
- 删除 = 调用 `DELETE /attachments/{id}/link/{entity_type}/{entity_id}`
- 提交目标时一并提交附件关联

### 6.2 GoalDetail / ProjectDetail / TaskDetail 页面

在详情页增加"附件"标签页：

```
[配置] [触发日志] [心跳日志] [负载] [待处理任务] [📎 附件(2)]

┌─────────────────────────────────────────┐
│  [➕ 上传附件]                           │
│                                         │
│  📄 需求文档.pdf  1.2 MB  2026-05-20    │
│     [下载] [取消关联]                    │
│                                         │
│  📊 原型图.png    3.4 MB  2026-05-20    │
│     [下载] [取消关联]                    │
└─────────────────────────────────────────┘
```

### 6.3 通用 AttachmentUploader 组件

设计一个可复用的 React 组件：

```tsx
<AttachmentUploader
    entityType="goal"
    entityId={goalId}
    maxSize={50 * 1024 * 1024}
    onUploadComplete={(attachment) => {...}}
    onDelete={(attachmentId) => {...}}
/>
```

---

## 7. 后端实现要点

### 7.1 FastAPI 配置

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 文件上传大小限制（50MB）
app.add_middleware(
    # ... 或用 UploadFile 的 max_file_size 参数
)
```

### 7.2 上传端点伪代码

```python
@router.post("/attachments/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    created_by: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    # 1. 校验
    _validate_entity_type(entity_type)
    _validate_file_size(file, MAX_SIZE)
    _validate_file_extension(file.filename, BLOCKED_EXTENSIONS)
    _validate_entity_exists(entity_type, entity_id, db)
    
    # 2. 计算 hash
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    
    # 3. 去重检查
    existing = db.query(Attachment).filter(
        Attachment.sha256_hash == sha256
    ).first()
    
    if existing:
        # 复用
        _create_link(db, existing.id, entity_type, entity_id, created_by)
        return {"attachment_id": existing.id, "reused": True, ...}
    
    # 4. 保存文件
    now = datetime.now()
    att_id = f"att-{uuid4().hex[:8]}"
    subdir = now.strftime("%Y/%m")
    storage_path = f"{ATTACHMENT_ROOT}/{subdir}/{att_id}_{safe_filename(file.filename)}"
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(content)
    
    # 5. 创建记录
    attachment = Attachment(
        id=att_id,
        filename=file.filename,
        file_path=storage_path,
        mime_type=file.content_type or guess_mime(file.filename),
        sha256_hash=sha256,
        file_size=len(content),
        created_by=created_by,
    )
    db.add(attachment)
    db.flush()
    
    _create_link(db, att_id, entity_type, entity_id, created_by)
    db.commit()
    
    return {"attachment_id": att_id, "reused": False, ...}
```

### 7.3 删除端点伪代码

```python
@router.delete("/attachments/{id}")
async def delete_attachment(
    id: str,
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    attachment = db.query(Attachment).filter(Attachment.id == id).first()
    if not attachment:
        raise HTTPException(404, "Attachment not found")
    
    # 检查关联数
    link_count = db.query(AttachmentLink).filter(
        AttachmentLink.attachment_id == id
    ).count()
    
    if link_count > 0 and not force:
        raise HTTPException(409, {
            "code": "ATTACHMENT_IN_USE",
            "message": f"此附件还被 {link_count} 个实体关联",
            "hint": "使用 ?force=true 强制删除所有关联"
        })
    
    # 删除 link
    db.query(AttachmentLink).filter(
        AttachmentLink.attachment_id == id
    ).delete()
    
    # 删除物理文件
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)
    
    # 删除记录
    db.delete(attachment)
    db.commit()
    
    return {"success": True}
```

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 磁盘写满 | 中 | 高 | 定期监控 + 告警，设置磁盘配额 |
| 恶意文件上传 | 低 | 高 | 黑名单 + MIME 校验 + 存储路径隔离 |
| hash 碰撞 | 极低 | 高 | SHA256 碰撞概率 ≈ 2^-128，可忽略 |
| 删除正在使用的附件 | 中 | 中 | 删除前检查 link 计数，409 拒绝 |
| 迁移丢数据 | 低 | 高 | 迁移脚本先 COPY 再 DROP，保留旧表备份 |

---

## 9. 实施计划

### Phase 1：基础设施（1-2天）
- [ ] DB 迁移脚本（创建新表 + 迁移旧数据）
- [ ] 后端上传 API
- [ ] 后端下载 API
- [ ] 后端删除 + 关联管理 API

### Phase 2：前端集成（1-2天）
- [ ] AttachmentUploader 通用组件
- [ ] CreateGoal 页面集成
- [ ] GoalDetail 附件标签页
- [ ] TaskDetail / ProjectDetail 附件标签页（按需）

### Phase 3：收尾
- [ ] 删除旧 `task_attachments` 表
- [ ] 更新相关文档
- [ ] E2E 验证（上传 → 关联 → 下载 → 删除）

---

## 10. 待定事项

| 事项 | 决策 | 状态 |
|------|------|------|
| sha256 去重 | ✅ v1 一次到位 | 已确认 |
| 存储路径统一 | ✅ `{root}/{year}/{month}/{id}_{filename}` | 已确认 |
| 文件大小限制 | ✅ 50MB 默认，可配置 | 已确认 |
| 文件类型限制 | ✅ 黑名单制 | 已确认 |
| 下载鉴权策略 | ✅ 走后端流式返回 | 已确认 |
| 存储根目录 | ✅ `.env` 配置，默认 `data/attachments` | 已确认 |
| 迁移旧数据 | ✅ Python 脚本迁移，保留旧表备份 | 已确认 |
