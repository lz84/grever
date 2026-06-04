# Sprint 53: Verifier Agent 完整设计与实现

> 三级验证机制 + 模型层合并的完整技术文档。后续追加功能基于此文档。

---

## 一、架构设计

### 1.1 核心思想

执行者和验收者分离。执行者 = 运动员，Verifier = 裁判。执行者报完成后，由独立的 Verifier Agent 按验收标准检查，通过才标记 done。

```
Executor Agent (coder/kouzi)          Verifier Agent (kouzi)
 │                                        │
 领任务 → 执行 → 报完成 ────────────→ 领验证 → 跑验收标准 → 通过/打回
```

### 1.2 三级继承链

Goal → Project → Task 三级都可以设置检查 Agent，子级优先于父级：

```
Task.verifier_agent_id
    ↓ (为空)
Project.verifier_agent_id
    ↓ (为空)
Goal.verifier_agent_id
    ↓ (为空)
kouzi (默认)
```

### 1.3 完整业务流（2026-05-05 更新：自动修复循环）

```
┌─────────────────────────────────────────────────────────────────────┐
│ Task Complete Flow (含自动修复循环)                                  │
│                                                                      │
│  1. Executor Agent 报完成 (POST /tasks/{id}/complete)                │
│     ↓                                                                │
│  2. complete_task API 检测 acceptance_criteria                        │
│     ├─ 无 → status=done, completed_at 设置, 正常流程                  │
│     └─ 有 → status=verifying, 推给 Verifier Agent                    │
│        ↓                                                             │
│  3. Verifier Agent 执行验证（加载对应 skill）                         │
│     ↓                                                                │
│  4. 验证结果                                                         │
│     ├─ 全部通过                                                       │
│     │   → 写 comment（详细验证通过意见）                              │
│     │   → status=done, completed_at 设置, 触发依赖解锁                 │
│     │                                                               │
│     └─ 有不通过                                                       │
│         → 写 comment（详细验证意见 + 不通过原因）                     │
│         → verification_cycle + 1                                     │
│         ↓                                                            │
│         if cycle < max_cycles (默认 3):                               │
│             → status = review_needed                                 │
│             → 自动派发回 Executor（附带 comment）                     │
│             → Executor 读 comment → 修复 → 重新报完成（回到步骤 2）   │
│         else:                                                         │
│             → status = disputed                                      │
│             → 转人工裁决中心                                          │
│             → 飞书通知 + 人工审核                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据库设计

### 2.1 迁移脚本

`migrations/015_verifier_agent.sql`:
```sql
ALTER TABLE goals ADD COLUMN verifier_agent_id TEXT NULL;
ALTER TABLE projects ADD COLUMN verifier_agent_id TEXT NULL;
ALTER TABLE tasks ADD COLUMN verifier_agent_id TEXT NULL;
```

### 2.2 相关列

| 表 | 列 | 类型 | 说明 |
|----|-----|------|------|
| goals | verifier_agent_id | TEXT | 目标的检查 Agent |
| projects | verifier_agent_id | TEXT | 项目的检查 Agent |
| tasks | verifier_agent_id | TEXT | 任务的检查 Agent |
| tasks | acceptance_criteria | TEXT | 验收标准（JSON） |
| tasks | status | TEXT | 新增 'verifying' 状态 |

---

## 三、API 端点

### 3.1 设置 Verifier

```
POST /api/v1/goals/{goal_id}/verifier
POST /api/v1/projects/{project_id}/verifier
POST /api/v1/tasks/{task_id}/verifier
Body: { "verifier_agent_id": "kouzi" }
```

### 3.2 查询有效 Verifier（含继承链）

```
GET /api/v1/tasks/{task_id}/verifier
Response:
{
  "task_id": "task-xxx",
  "effective_verifier": "kouzi",
  "inheritance_chain": {
    "task_verifier": null,
    "project_verifier": "kouzi",
    "goal_verifier": null,
    "default_verifier": "kouzi"
  }
}
```

### 3.3 手动触发验证

```
POST /api/v1/tasks/{task_id}/verify
Response:
{
  "task_id": "task-xxx",
  "passed": true,
  "action": "done",
  "verifier_agent": "kouzi",
  "unlocked_tasks": ["task-yyy"]
}
```

### 3.4 任务完成（自动路由）

```
POST /api/v1/tasks/{task_id}/complete
Body: {
  "status": "done",
  "result": "执行结果描述",
  "execution_log": { "agent": "kouzi", "success": true },
  "duration_ms": 5000
}

→ 有 acceptance_criteria: status = verifying
→ 无 acceptance_criteria: status = done
```

---

## 四、核心代码

### 4.1 ResultVerifier 类

`reins/scheduler/result_verifier.py`:

```python
class ResultVerifier:
    DEFAULT_VERIFIER = "kouzi"

    def resolve_effective_verifier(self, task_id: str) -> str:
        """三级继承链解析"""
        # Task → Project → Goal → DEFAULT_VERIFIER

    def trigger_verification(self, task_id: str, result: str, success: bool) -> Dict:
        """触发验证流程"""
        # 1. 解析 verifier
        # 2. 设 status=verifying
        # 3. 跑 _run_verifier_checks()
        # 4. 通过 → done, 不通过 → review_needed

    def _run_verifier_checks(self, task_id: str, result: str) -> Tuple[bool, str]:
        """运行验收标准"""
        # 解析 acceptance_criteria JSON
        # 根据 type 执行对应检查: compile/api/page/custom
```

### 4.2 complete_task 改动

`reins/api/tasks.py` 关键逻辑：

```python
# 检测是否有验收标准
has_acceptance_criteria = task.acceptance_criteria is not None and task.acceptance_criteria.strip() != ""

if request.status == "done":
    if not validation_passed:
        task.status = "review_needed"
    elif has_acceptance_criteria:
        task.status = "verifying"  # 自动进入验证状态
        task.result_summary = request.result
    else:
        task.status = "done"

# verifying 状态：记录结果但不设 completed_at
if task.status == "verifying":
    task.result = request.result
    task.result_summary = request.result
elif request.status == "done":
    task.completed_at = datetime.now()
    task.result = request.result
```

---

## 五、模型层统一

### 5.1 问题

之前 `schemas/` 和 `models/` 两套独立维护，加字段时漏了一边导致数据丢失。

### 5.2 方案

`reins/models/schema_factory.py` — 从 SQLAlchemy ORM 自动生成 Pydantic schema：

```python
def auto_schema(orm_class, create_exclude=None, update_exclude=None, create_defaults=None):
    """返回 (CreateSchema, UpdateSchema, ResponseSchema)"""
    # 从 ORM 列定义自动推导
```

### 5.3 使用方式

```python
# models/task.py
TaskCreate, TaskUpdate, TaskResponse = auto_schema(
    Task,
    create_defaults={'status': 'todo', 'priority': 'medium'},
)

# 添加虚拟字段（非 DB 列）
TaskCreate = create_model('TaskCreate', __base__=TaskCreate, dependency_ids=(Optional[list[str]], None))
```

### 5.4 清理

- 删除 `schemas/` 目录（11 个文件）
- Task/Goal/Project → 自动推导
- Scenario/Security → 复杂嵌套模型手动定义，统一在 models/ 里

---

## 六、E2E 测试覆盖

42 个测试全部通过，覆盖 5 个场景：

| 场景 | 测试数 | 验证点 |
|------|--------|--------|
| 三级 verifier 设置 + 继承链 | 11 | Task→Project→Goal→default 回退 |
| 无验收标准 → 直接 done | 4 | status=done, completed_at 设置 |
| 有验收标准 → verifying → verify → done | 8 | 自动路由, 手动触发, completed_at 时机 |
| 有验收标准 → verify 失败 → review_needed | 8 | 失败检测, error_message 记录 |
| 完整继承链验证 | 2 | 多级回退正确性 |

测试文件：`packages/server/temp/test_verifier_flow.py`

---

## 七、Git 提交

| Commit | 说明 |
|--------|------|
| `11dd668` | feat: three-level Verifier Agent inheritance chain |
| `d5e82a2` | fix: Verifier Agent schemas and ORM fixes |
| `7dec169` | refactor: merge schemas/ into models/ |
| `fdcef2b` | docs: add architecture decisions log |

---

## 八、后续扩展 TODO

### 已实现（2026-05-04）

- [x] `waiting_human` 状态实现（Sprint 56）
- [x] 通知机制（飞书通知，Sprint 56）
- [x] 超时处理（Sprint 56）
- [x] Session ID 隔离解决 Worker 文件锁冲突
- [x] DAG 工作流配置（Sprint 55）
- [x] 人类输入详情页重写（2026-05-05 凌晨）— 三段式解释 + 条件显示拒绝原因

### 待实现

- [ ] 人类输入是否走 Verifier 检查
- [ ] human_input_requests 表优化（索引、约束）
- [ ] 批量处理人类输入请求
- [ ] 监控仪表板（waiting_human 任务概览、超时预警）
- [ ] 表单自动生成（根据 human_input_schema 渲染表单）

### 可扩展方向

- [ ] Verifier Agent 独立 Worker（不直接在后端进程内跑，而是通过 openclaw agent CLI）
- [ ] 多 Verifier 并行（编译检查 + API 检查同时跑）
- [ ] 验证历史（记录每次验证的通过/不通过记录）
- [ ] 验证评分（根据通过率给 Agent 打分）
- [ ] 自动重试（验证不通过自动分配给另一个 Agent 重做）

---

## 十二、通用验证策略扩展（2026-05-05 新增）

### 12.0 核心设计原则（2026-05-05 用户确认）

1. **Agent 全面接管验证**：不用 Python 程序做客观检测，所有验证统一由 Verifier Agent 执行
2. **Skill 可插拔**：不同验证类型 = 不同 Skill（verify-compile、verify-api、verify-design 等），新增验证类型只需创建新 Skill
3. **验证意见写入 comment**：Agent 验证结果必须写入 `task_comments` 表，包含详细验证过程和意见，供人工裁决中心使用
4. **ResultVerifier 仅做分发**：Python 只负责解析 acceptance_criteria、创建验证任务、派给 Worker、收结果、更新状态

**完整流程**：
```
Executor Agent 报完成
    ↓
ResultVerifier (Python, 薄分发层)
    ├─ 解析 acceptance_criteria
    ├─ 创建验证任务 → 推给 Nexus Worker
    │
    ↓
Verifier Agent (Agent + Skills)
    ├─ 领任务
    ├─ 按需加载 skill（verify-compile / verify-api / verify-design / ...）
    ├─ 执行验证
    ├─ 写验证意见到 task_comments（详细过程 + 结论）
    └─ 返回结果
    ↓
ResultVerifier 汇总
    ├─ 全部通过 → status = done, completed_at 设置
    └─ 有不通过
        ├─ cycle < 3 → status = review_needed → 自动派发回 Executor
        │   └─ Executor 读 comment → 修复 → 重新报完成（正向循环）
        └─ cycle >= 3 → status = disputed → 转人工裁决中心
            └─ 人工可看到所有 comment 历史，辅助决策
```

### 12.0.1 自动修复循环（2026-05-05 核心设计）

**正向循环机制**：
1. Verifier 不通过 → 写 comment 到 `task_comments`
2. 自动派发回 Executor，Executor 能看到所有历史 comment
3. Executor 根据 comment 修复 → 重新报完成
4. 回到 Verifier 再次验证
5. 最多循环 3 次，超过 → 转人工裁决

**comment 格式**（写入 `task_comments` 表）：
```json
{
  "author_role": "verifier",
  "type": "verification_result",
  "content": "验证结果：不通过\n\n❌ API 返回 200，但缺少 disputed_count 字段\n✅ 其他字段结构正确\n\n建议：在 stats API 响应中增加 disputed_count 字段",
  "metadata": {
    "verification_cycle": 2,
    "passed": false,
    "checks": [
      {"name": "compile", "passed": true},
      {"name": "api", "passed": false, "detail": "缺少 disputed_count 字段"}
    ]
  }
}
```

Executor 重新领取任务时，自动附带最近的 verification comment，让 Executor 知道哪里需要改。

### 12.1 设计动机

ResultVerifier 初始设计偏向编程任务（编译、API 测试），但实际任务类型多样：

| 任务类型 | 验证挑战 |
|---------|---------|
| 编程任务 | ✅ 已支持（编译、API curl、页面验证） |
| 文档类 | ❓ 文件是否存在？内容是否完整？ |
| 设计类 | ❓ 方案是否合理？格式是否规范？ |
| 内容类 | ❓ 关键词是否覆盖？准确性如何？ |
| 配置类 | ❓ 配置文件语法是否正确？ |

**原则**：自动验证能做多少做多少，不够的走人工审核（`review_needed` → 人类裁决中心）。

### 12.2 验证策略矩阵

#### 策略 A：文件验证（File Verification）

适用于：文档、配置、设计稿等非编程类产出。

| 检查项 | 实现方式 | 适用任务类型 |
|--------|---------|-------------|
| 文件存在 | `os.path.exists(file_path)` | 所有文件类 |
| 文件大小 | `os.path.getsize(file_path) >= min_bytes` | 文档/设计 |
| 文件格式 | 后缀匹配 `.md`/`.json`/`.yaml` | 文档/配置 |
| 内容行数 | `len(open(f).readlines()) >= min_lines` | 文档 |
| 关键词覆盖 | 遍历 acceptance_criteria.keywords，检查是否包含 | 内容/文档 |
| 结构检查 | Markdown 必须有 `#` header，JSON 必须可解析 | 文档/配置 |

**acceptance_criteria 配置示例**：
```json
{
  "type": "file",
  "file_path": "D:/work/research/agents-nexus/docs/sprint-xxx-plan.md",
  "min_bytes": 1024,
  "min_lines": 10,
  "keywords": ["需求分析", "技术方案", "排期"],
  "format": "markdown"
}
```

#### 策略 B：API 验证（API Verification）— 已有

```json
{
  "type": "api",
  "desc": "stats API 返回 200",
  "endpoint": "http://localhost:8090/api/v1/human-review/stats",
  "method": "GET",
  "expect_status": 200,
  "expect_keys": ["disputed_count", "pending_assist_count"]
}
```

#### 策略 C：编译验证（Compile Verification）— 已有

```json
{
  "type": "compile",
  "command": "python -m py_compile src/reins/services/xxx.py",
  "work_dir": "D:/work/research/agents-nexus"
}
```

#### 策略 D：LLM 辅助验证（LLM-Assisted Verification）— 新增

适用于：设计质量评估、内容准确性、方案合理性等需要主观判断的场景。

**流程**：
1. Verifier 读取任务描述 + 产出文件内容
2. 拼接 prompt："任务要求是 X，产出是 Y。请按以下标准评分（1-5）：[标准列表]"
3. 调用 LLM（kouzi agent），得到评分和评语
4. 评分 ≥ 阈值 → 通过，否则 → review_needed

**acceptance_criteria 配置示例**：
```json
{
  "type": "llm_review",
  "criteria": [
    "内容是否覆盖任务描述的所有要点",
    "文档结构是否清晰（有标题分段）",
    "技术术语是否准确",
    "是否有明显的逻辑矛盾"
  ],
  "min_score": 3,
  "max_score": 5
}
```

**实现伪代码**：
```python
def _run_llm_review(task_id, result_text, criteria):
    """用 LLM 做主观质量评估"""
    # 1. 读取产出文件
    files = extract_produced_files(result_text)
    content = read_files_content(files)
    
    # 2. 构造 prompt
    prompt = f"""你是一名技术评审员。
任务描述：{task_description}
产出内容：{content}

请按以下标准评分（1-5 分）：
{criteria}

返回 JSON 格式：{{"scores": [1-5], "total": x, "comment": "评审意见"}}"""
    
    # 3. 调用 LLM（通过 Nexus Worker）
    llm_response = call_kouzi(prompt, max_tokens=500)
    
    # 4. 解析结果
    scores = parse_json(llm_response)
    passed = scores["total"] >= min_score
    return passed, scores["comment"]
```

#### 策略 E：自定义脚本验证（Custom Script）— 已有扩展

```json
{
  "type": "custom",
  "script": "scripts/verify_sprint_xxx.py",
  "args": ["--project-id", "proj-xxx"]
}
```

### 12.3 验证策略优先级

当任务有多个验收标准时，按以下顺序执行：

```
1. 编译检查（快速失败，cost 最低）
2. 文件验证（本地文件系统，cost 低）
3. API 验证（网络请求，cost 中）
4. 自定义脚本（可能耗时，cost 中）
5. LLM 辅助验证（调 LLM，cost 最高）
```

### 12.4 无法自动验证 → 人工审核

如果任务的 acceptance_criteria 只包含无法自动检查的条目（如"方案是否美观"），ResultVerifier 会：

1. 跳过自动验证（无匹配策略）
2. 直接设 `status = review_needed`
3. 通过飞书通知人类
4. 人类在裁决中心审核（`/human-review` 页面）

### 12.5 扩展 acceptance_criteria schema

```json
{
  "criteria": [
    {
      "type": "compile|api|page|file|llm_review|custom",
      "desc": "人类可读的验收描述",
      // compile
      "command": "python -m py_compile xxx.py",
      "work_dir": "D:/work/research/agents-nexus",
      // api
      "endpoint": "http://localhost:8090/api/v1/xxx",
      "method": "GET",
      "expect_status": 200,
      "expect_keys": ["key1", "key2"],
      // file
      "file_path": "path/to/file.md",
      "min_bytes": 1024,
      "min_lines": 10,
      "keywords": ["关键词1", "关键词2"],
      "format": "markdown|json|yaml",
      // llm_review
      "criteria": ["标准1", "标准2"],
      "min_score": 3,
      // custom
      "script": "scripts/verify_xxx.py",
      "args": ["--flag"]
    }
  ]
}
```

### 12.6 验证报告格式

每次验证完成后，生成结构化报告存入 `task_comments` 表：

```json
{
  "task_id": "task-xxx",
  "verifier": "kouzi",
  "verification_cycle": 1,
  "results": [
    {"type": "compile", "status": "pass", "detail": "py_compile OK"},
    {"type": "api", "status": "pass", "detail": "HTTP 200 + JSON 结构正确"},
    {"type": "file", "status": "pass", "detail": "sprint-xxx.md 存在，5.2KB，120 行，关键词覆盖率 100%"},
    {"type": "llm_review", "status": "pass", "detail": "评分 4/5，结构清晰"}
  ],
  "overall": "pass",
  "comment": "4/4 验收标准通过",
  "timestamp": "2026-05-05T21:30:00"
}
```

### 12.7 实施计划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 文件验证策略（file）| P0 |
| Phase 2 | LLM 辅助验证（llm_review）| P1 |
| Phase 3 | 验证报告结构化 + task_comments 存储 | P1 |
| Phase 4 | 人类裁决中心整合 review_needed 任务 | P0（已在 Sprint 58） |

---

<!-- 后续追加到此文件 -->

## 九、实施记录（2026-05-04/05）

### Sprint 55: DAG 流程配置验证（5月4日 12:15-12:49）

- 创建 Goal + Project + 5 个任务，通过 `from-goal` API 创建 Workflow
- 设置任务依赖和 workflow_steps 依赖（JSON 格式）
- 发现并修复 GoalStatus 枚举冲突

### Sprint 56: Verifier Agent 人在环路 + 通知 + 超时（5月4日 20:45-21:20）

- waiting_human 状态实现
- 飞书通知机制
- 超时处理
- Worker 改进：Session ID 隔离、Batch 模式、30 分钟超时
- complete_task API 修复（需要 duration_ms 字段）

### 人类输入详情页优化（5月5日 凌晨）

**问题**: 用户反馈详情页信息不足，不知道请求来源、原因、该做什么，且按钮逻辑混乱（确认/取消 vs 拒绝原因）

**修复**:
1. 新增三段式解释区域：📋 是什么 / ❓ 为什么 / ✅ 做什么
2. 拒绝原因改为条件显示（点击否决后才出现）
3. 列表页点击项时调详情 API 获取完整数据
4. Vite Proxy 500 修复：杀掉旧后端进程，context 字段正确解析

---

## 十、已知 Bug 清单（2026-05-05 06:50 发现）

### Bug 1 (P0): review_needed → complete 返回 500

**现象**: 任务验证失败变成 `review_needed` 后，Executor 重新提交 `POST /tasks/{id}/complete` 时返回 500 Internal Server Error。

**根因**: `complete_task` 中当 `is_redispatch=True`（从 review_needed 重新提交），代码先做了 `db.commit()` 把状态改为 verifying，然后调 `trigger_verification()`。但 `trigger_verification` 内部用 `get_db_manager()` 创建独立 DB 连接（raw SQLAlchemy engine），和当前的 ORM session 冲突，导致 SQLite 锁竞争或 session 状态异常。

**调用链**:
```
complete_task (ORM session)
  → db.commit()                      # 提交了 verifying 状态
  → trigger_verification()
     → self.db.engine.connect()      # 独立连接，和 ORM session 冲突
        → UPDATE tasks ...           # 锁竞争或 session 异常
  → 500 Internal Server Error
```

**修复方向**:
1. 方案 A：在 `trigger_verification` 中复用调用方的 session，不创建独立连接
2. 方案 B：在 `complete_task` 中给 `trigger_verification` 调用加 try/except，捕获异常后回滚
3. 方案 C（推荐）：合并为一个事务——`complete_task` 中不要提前 commit，等 `trigger_verification` 完成后再统一 commit

**影响范围**: 所有带验收标准的任务，验证失败后无法自动修复循环

### Bug 2 (P1): verification_cycle 计数多 1

**现象**: 3 次验证失败后，`verification_cycle = 4` 而不是预期的 `3`。

**根因**: `result_verifier.py` 的 `trigger_verification` 中，每次调用都执行 `cycle = current_cycle + 1`。但 `complete_task` 的 redispatch 路径中，在调 `trigger_verification` 之前可能已经递增过 cycle，或者 `trigger_verification` 被重复调用导致双重递增。

**E2E 测试结果**:
```
Cycle 1: verify → review_needed, cycle=1 ✅
Cycle 2: complete → 500 (Bug 1 触发)
Cycle 3: complete → 500（但意外触发 disputed）
最终: cycle=4 ❌
```

**修复方向**: 确保 cycle 只在 `trigger_verification` 内部递增一次，不在其他地方递增。`complete_task` 的 redispatch 路径中不要手动改 cycle。

### Bug 3 (P0): heartbeat 不派发 review_needed 任务

**现象**: `assignment.py` 的 `assign_tasks_to_agent` 查询条件只查 `status IN ('todo', 'pending')`，不包含 `review_needed`。验证失败后任务无法通过心跳自动重新派发。

**根因**: SQL 查询遗漏了 review_needed 状态。设计文档（16-verification-communication-design.md）中明确要求 heartbeat 检测 review_needed 任务并重新派发，但代码实现未覆盖。

**修复方向**:
```sql
-- 原来
WHERE status IN ('todo', 'pending')

-- 修复后
WHERE status IN ('todo', 'pending', 'review_needed')
```

同时派发时附带最近的 verification comment 内容，让 Executor 知道哪里需要改。

### Bug 修复进度

| Bug | 状态 | 负责人 | 预计完成 |
|-----|------|--------|---------|
| Bug 1 (P0): complete 500 | 🔴 修复中 | 扣子 | 2026-05-05 |
| Bug 2 (P1): cycle 多 1 | 🟡 修复中 | 扣子 | 2026-05-05 |
| Bug 3 (P0): heartbeat 缺 review_needed | 🔴 修复中 | 扣子 | 2026-05-05 |

---

## 十一、服务稳定性保障 — Watchdog 看门狗（2026-05-05 07:05）

### 11.1 设计动机

Nexus 后端（uvicorn）和前端（Vite dev server）可能因以下原因崩溃：
- Python 异常 / 内存溢出
- SIGKILL 被系统或 OpenClaw session 清理机制杀死
- 端口占用导致启动失败
- 开发环境手动 Ctrl+C 后忘记重启

### 11.2 架构

```
bin/start.ps1 启动
  ├─→ scripts/watchdog.py --daemon（后台独立进程）
  │    ├─ 每 30 秒 HTTP 健康检查
  │    ├─ 后端: GET /docs → 200
  │    ├─ 前端: GET / → 200
  │    ├─ 连续 2 次失败 → 自动重启
  │    ├─ 最多重启 3 次后放弃
  │    └─ --daemon 模式: watchdog 自身崩溃也自动重启
  │
  └─→ scripts/dev-runner.mjs（后端 + 前端）
       ├─ uvicorn (8090)
       └─ npm run dev (5173)
```

**关键特性**:
- **独立于 dev-runner 生命周期** — 即使 dev-runner 被 Ctrl+C 杀死，watchdog 仍持续运行
- **连续失败才触发** — 避免网络抖动误判（连续 2 次失败）
- **有限重启** — 最多重启 3 次，避免无限重启循环
- **日志记录** — 所有检查/重启操作写入 `logs/watchdog-YYYYMMDD.log`

### 11.3 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHECK_INTERVAL` | 30s | 健康检查间隔 |
| `MAX_RETRIES` | 2 | 连续失败几次后触发重启 |
| `MAX_RESTARTS` | 3 | 最多重启次数 |
| `RESTART_COOLDOWN` | 10s | 重启冷却时间 |

### 11.4 验证结果

```
✅ 检测后端 8090 — 已运行，HTTP 200
✅ 检测前端 5173 — 未运行，2 次失败后自动触发重启
✅ 重启逻辑 — 找到旧 PID → taskkill → 启动新进程
✅ 日志输出 — logs/watchdog-20260505.log
```

### 11.5 文件位置

- 看门狗: `scripts/watchdog.py`
- 集成点: `bin/start.ps1`（启动时自动用 `Start-Process` 后台运行）
- 日志: `logs/watchdog-YYYYMMDD.log`


---


# Sprint 54: Verifier-Executor 沟通机制设计

> 基于 Comment 的验证循环 + Heartbeat 派发 + 人工裁决。基于 Sprint 53（三级 Verifier）之上的扩展。

---

## 一、核心设计原则

1. **Comment 是沟通载体** — Verifier 的验证意见通过 `task_comments` 表传递，Executor 通过读 comment 知道自己该改什么
2. **Heartbeat 驱动派发** — 不新增派发代码，利用现有心跳机制检测 `review_needed` 任务并重新派发
3. **全量验证** — 每次验证都跑全部验收标准，不做增量优化
4. **3 次循环上限** — 超过 3 次转人工裁决
5. **人工裁决为中心** — 裁决后 Executor 和 Verifier 都围绕人类意见执行，不引入新角色

---

## 二、完整业务流程

### 2.1 正常验证循环（≤3 次）

```
Executor 报完成 (POST /tasks/{id}/complete)
    ↓
ResultVerifier.trigger_verification()
    ↓
_run_verifier_checks() — 全量跑所有验收标准
    ↓
├─ 全部通过
│   → 写入 comment(type="verification", body="✅ 验证通过: [详情]")
│   → status=done
│   → completed_at 设置
│   → 解锁依赖任务
│
└─ 有不通过
    → 写入 comment(type="verification", body="❌ 验证失败: [逐项结果]")
    → status=review_needed
    → verification_cycle++
    → completed_at 不设
    ↓
等下次 Heartbeat（30s）
    ↓
Heartbeat 发现 review_needed 任务
    → 读取最近的 verification comment
    → 重新派给同一个 Executor
    ↓
Executor 领任务时附带 comment 内容
    → 知道哪里要改
    → 修改 → 报完成
    ↓
重复验证流程
```

### 2.2 3 次循环后转人工

```
verification_cycle >= 3 且仍不通过
    ↓
status=disputed
    ↓
写入 comment(type="verification", body="⚠️ 3次验证未通过，转人工裁决")
    ↓
通知人类（飞书消息 / 前端通知）
    ↓
等待人工介入
```

### 2.3 人工裁决流程

```
人类介入
    ↓
写入 comment(type="human_ruling", body="裁决意见: [详细说明]")
    ↓
人类指定下一步动作:
    ├─ 通过 → status=done
    ├─ 打回 → status=in_progress, Executor 按裁决意见修改
    └─ 部分通过 → status=verifying, Verifier 按裁决意见调整验收标准
    ↓
Executor 按人类意见执行
    ↓
Verifier 按人类意见验证
    ↓
（不引入新的 Executor，原 Executor 继续）
```

---

## 三、Comment 类型定义

| type 值 | 写入者 | 说明 |
|---------|--------|------|
| `verification` | Verifier Agent | 验证结果，包含逐项 pass/fail/detail |
| `human_ruling` | 人类用户 | 人工裁决意见 |
| `executor_response` | Executor Agent | 执行者对验证意见的响应（可选） |

### verification comment 格式

```json
{
  "task_id": "task-xxx",
  "author": "kouzi",
  "author_role": "verifier",
  "type": "verification",
  "body": "❌ 验证失败 (cycle 2/3)\n\n编译检查: ❌ 3 errors in Pagination.tsx\nAPI 检查: ✅ /api/v1/tasks 返回 200\n页面检查: ✅ 页面正常渲染\n\n请修复编译错误后重新提交。",
  "created_at": "2026-05-04T10:30:00Z",
  "metadata": {
    "verification_cycle": 2,
    "checks": [
      {"name": "compile", "passed": false, "detail": "3 errors in Pagination.tsx"},
      {"name": "api", "passed": true, "detail": "/api/v1/tasks 返回 200"},
      {"name": "page", "passed": true, "detail": "页面正常渲染"}
    ]
  }
}
```

### human_ruling comment 格式

```json
{
  "task_id": "task-xxx",
  "author": "用户",
  "author_role": "human",
  "type": "human_ruling",
  "body": "裁决: 编译错误可以忽略，这是已知问题。API 和页面检查已通过，标记为 done。",
  "created_at": "2026-05-04T11:00:00Z",
  "metadata": {
    "ruling_action": "done",
    "overrides_verification": true
  }
}
```

---

## 四、数据库现状与变更

### 4.1 现状（Sprint 54 开始前）

| 表 | 状态 | 说明 |
|----|------|------|
| `tasks` | ✅ 存在 | 已有 `verifier_agent_id`, `acceptance_criteria`, `verification_cycle` 不存在 |
| `task_comments` | ❌ **不存在** | Sprint 42 API 代码写了（`task_features.py`），但表没创建 |
| `comments` | ❌ 不存在 | 无此表 |

**结论**：需要创建 `task_comments` 表 + 给 `tasks` 加 `verification_cycle` 列。

### 4.2 迁移脚本

`migrations/016_verification_cycle_and_comments.sql`:

```sql
-- 1. tasks 表加 verification_cycle 列
ALTER TABLE tasks ADD COLUMN verification_cycle INT DEFAULT 0;

-- 2. 创建 task_comments 表
CREATE TABLE IF NOT EXISTS task_comments (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(32) NOT NULL,
    author VARCHAR(64) NOT NULL,
    author_role VARCHAR(32) DEFAULT 'agent',
    type VARCHAR(32) DEFAULT 'comment',
    content TEXT NOT NULL,
    is_agent_reply INT DEFAULT 0,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 3. 创建索引（加速查询）
CREATE INDEX IF NOT EXISTS idx_task_comments_task_id ON task_comments(task_id);
CREATE INDEX IF NOT EXISTS idx_task_comments_type ON task_comments(type);
```

---

## 五、需要改的文件（实际路径）

| # | 文件 | 改动 |
|---|------|------|
| 1 | `packages/server/migrations/016_verification_cycle_and_comments.sql` | 新建：verification_cycle 列 + task_comments 表 |
| 2 | `packages/server/src/reins/models/task.py` | 加 `verification_cycle` 列 + `TaskStatus.DISPUTED` |
| 3 | `packages/server/src/reins/models/base.py` | 加 `TaskComment` ORM 模型 |
| 4 | `packages/server/src/reins/scheduler/result_verifier.py` | 改造：写 comment + cycle 计数 + disputed 逻辑 |
| 5 | `packages/server/src/reins/api/assignment.py` | 改造：Heartbeat 检测 review_needed + 附带 comment 派发 |
| 6 | `scripts/agent_worker.py` | 改造：领任务时读取最近的 verification comment |
| 7 | `packages/server/src/reins/api/tasks.py` | 新增：ruling API + verifications API + disputed 支持 |
| 8 | `packages/server/src/reins/api/task_features.py` | 修复：现有 comment API 指向正确的 task_comments 表 |
| 9 | `packages/server/src/utils/statusMap.ts` | 前端：新增 `disputed` 状态映射 |
| 10 | `packages/server/src/api/tasks.ts` | 前端 API：ruling + verifications + disputed |
| 11 | 前端页面（TaskList/Dashboard） | disputed badge + cycle 显示 + 裁决入口 |

---

## 六、API 端点

### 6.1 提交人工裁决（新增）

```
POST /api/v1/tasks/{task_id}/ruling
Body: {
  "ruling": "裁决意见",
  "action": "done | in_progress | verifying"
}
Response: {
  "task_id": "task-xxx",
  "status": "done",
  "ruling_comment_id": "comment-yyy"
}
```

### 6.2 查询验证历史（新增）

```
GET /api/v1/tasks/{task_id}/verifications
Response: [
  {
    "cycle": 1,
    "type": "verification",
    "verifier": "kouzi",
    "passed": false,
    "checks": [...],
    "body": "...",
    "created_at": "2026-05-04T10:30:00Z"
  },
  {
    "type": "human_ruling",
    "author": "用户",
    "ruling_action": "done",
    "body": "...",
    "created_at": "2026-05-04T11:00:00Z"
  }
]
```

### 6.3 现有端点行为变更

| 端点 | 变更 |
|------|------|
| `POST /tasks/{id}/complete` | 有验收标准且 cycle < 3 → review_needed + 写 comment；cycle ≥ 3 → disputed |
| `POST /tasks/{id}/verify` | 同上，验证失败时写 comment + cycle++ |
| Heartbeat 心跳 | 新增：扫描 review_needed 任务，附带 comment 重新派发 |

---

## 七、状态机

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      │
todo → in_progress → verifying → review_needed ────────────┘
    │                  │           │
    │                  │           │ (cycle < 3)
    │                  │           ↓
    │                  │     review_needed → in_progress（重新派发）
    │                  │           │
    │                  │           │ (cycle >= 3)
    │                  │           ↓
    │                  │     disputed → [human_ruling] → done/in_progress
    │                  │
    │                  │ (通过)
    │                  ↓
    │              done
    │
    └── on_hold
```

---

## 八、详细代码设计

### 8.1 TaskComment ORM 模型（新建）

```python
# packages/server/src/reins/models/base.py（或新建 comment.py）

from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class TaskComment(Base):
    __tablename__ = 'task_comments'

    id = Column(String(36), primary_key=True)
    task_id = Column(String(32), ForeignKey('tasks.id'), nullable=False)
    author = Column(String(64), nullable=False)
    author_role = Column(String(32), default='agent')  # agent / verifier / human
    type = Column(String(32), default='comment')  # comment / verification / human_ruling / executor_response
    content = Column(Text, nullable=False)
    is_agent_reply = Column(Integer, default=0)
    metadata = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship('Task', backref='comments')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'task_id': self.task_id,
            'author': self.author,
            'author_role': self.author_role,
            'type': self.type,
            'content': self.content,
            'is_agent_reply': bool(self.is_agent_reply),
            'metadata': json.loads(self.metadata) if self.metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

### 8.2 ResultVerifier 改造

```python
# packages/server/src/reins/scheduler/result_verifier.py

class ResultVerifier:
    DEFAULT_VERIFIER = "kouzi"
    MAX_VERIFICATION_CYCLES = 3

    def trigger_verification(self, task_id: str, result: str, success: bool) -> Dict:
        task = self.db.get_task(task_id)
        verifier = self.resolve_effective_verifier(task_id)
        passed, detail = self._run_verifier_checks(task_id, result)
        cycle = getattr(task, 'verification_cycle', 0) or 0

        if passed:
            self._write_verification_comment(task_id, verifier, cycle + 1, True, detail)
            task.status = "done"
            task.completed_at = datetime.now()
            task.result_summary = result
            self.db.commit()
            self._unlock_dependent_tasks(task_id)
            return {"passed": True, "action": "done"}
        else:
            cycle += 1
            if cycle >= self.MAX_VERIFICATION_CYCLES:
                # 超过上限 → disputed
                self._write_verification_comment(task_id, verifier, cycle, False, detail)
                self._write_verification_comment(
                    task_id, verifier, cycle, None,
                    f"⚠️ {cycle}次验证未通过，转人工裁决"
                )
                task.status = "disputed"
                task.verification_cycle = cycle
                task.result_summary = result
                task.error_message = detail
                self.db.commit()
                self._notify_human(task_id, cycle, detail)
                return {"passed": False, "action": "disputed", "verification_cycle": cycle}
            else:
                # cycle < 3 → review_needed，等 heartbeat 重新派发
                self._write_verification_comment(task_id, verifier, cycle, False, detail)
                task.status = "review_needed"
                task.verification_cycle = cycle
                task.result_summary = result
                task.error_message = detail
                self.db.commit()
                return {"passed": False, "action": "review_needed", "verification_cycle": cycle}

    def _write_verification_comment(self, task_id, verifier, cycle, passed, detail):
        from reins.models.base import TaskComment
        import json
        checks = self._parse_checks_from_detail(detail)
        status_icon = "✅" if passed else ("⚠️" if passed is None else "❌")
        body = f"{status_icon} 验证{'通过' if passed else ('未通过' if passed is False else '')} (cycle {cycle}/{self.MAX_VERIFICATION_CYCLES})\n\n{detail}"

        comment = TaskComment(
            id=f"cmt-{uuid4().hex[:8]}",
            task_id=task_id,
            author=verifier,
            author_role="verifier",
            type="verification",
            content=body,
            metadata=json.dumps({
                "verification_cycle": cycle,
                "passed": passed,
                "checks": checks
            }),
            created_at=datetime.now()
        )
        self.db.session.add(comment)
        self.db.session.commit()
        return comment.id
```

### 8.3 Heartbeat/Assignment 改造

```python
# packages/server/src/reins/api/assignment.py — heartbeat 端点中新增

def _assign_review_tasks(self, db, agent_id: str):
    """检测 review_needed 任务并重新派发给原 Executor"""
    from sqlalchemy import text
    tasks = db.execute(text("""
        SELECT * FROM tasks
        WHERE status = 'review_needed'
          AND assigned_agent = :agent_id
          AND verification_cycle < 3
    """), {"agent_id": agent_id}).fetchall()

    for task in tasks:
        # 优先检查人工裁决
        ruling = db.execute(text("""
            SELECT * FROM task_comments
            WHERE task_id = :task_id AND type = 'human_ruling'
            ORDER BY created_at DESC LIMIT 1
        """), {"task_id": task.id}).fetchone()

        # 其次检查验证意见
        comment = db.execute(text("""
            SELECT * FROM task_comments
            WHERE task_id = :task_id AND type = 'verification'
            ORDER BY created_at DESC LIMIT 1
        """), {"task_id": task.id}).fetchone()

        if ruling:
            db.execute(text("""
                UPDATE tasks SET status = 'in_progress',
                    ruling_comment_id = :ruling_id,
                    ruling_instruction = :ruling_body
                WHERE id = :task_id
            """), {"ruling_id": ruling.id, "ruling_body": ruling.content, "task_id": task.id})
        elif comment:
            db.execute(text("""
                UPDATE tasks SET status = 'in_progress',
                    instruction_comment_id = :comment_id
                WHERE id = :task_id
            """), {"comment_id": comment.id, "task_id": task.id})

        db.commit()
```

### 8.4 Worker 改造

```python
# scripts/agent_worker.py

def _build_task_prompt(self, task: Dict) -> str:
    prompt = f"任务: {task['title']}\n描述: {task['description']}\n"

    if task.get('ruling_instruction'):
        prompt += f"\n👤 人工裁决意见:\n{task['ruling_instruction']}\n请按人类裁决意见执行。\n"
    elif task.get('instruction_comment_id'):
        comment = self.api.get_comment(task['instruction_comment_id'])
        prompt += f"\n⚠️ 这是重新派发的任务。\n验证意见:\n{comment['content']}\n请根据上述验证意见修复后重新提交。\n"

    return prompt
```

### 8.5 人工裁决 API

```python
# packages/server/src/reins/api/tasks.py

@router.post("/tasks/{task_id}/ruling")
async def submit_ruling(task_id: str, request: RulingRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != "disputed":
        raise HTTPException(400, f"只有 disputed 状态的任务可以提交裁决，当前状态: {task.status}")

    from reins.models.base import TaskComment
    comment = TaskComment(
        id=f"cmt-{uuid4().hex[:8]}",
        task_id=task_id,
        author="human",
        author_role="human",
        type="human_ruling",
        content=request.ruling,
        metadata=json.dumps({"ruling_action": request.action}),
        created_at=datetime.now()
    )
    db.add(comment)

    if request.action == "done":
        task.status = "done"
        task.completed_at = datetime.now()
    elif request.action == "in_progress":
        task.status = "in_progress"
        task.verification_cycle = 0
    elif request.action == "verifying":
        task.status = "verifying"

    db.commit()
    return {"task_id": task_id, "status": task.status, "ruling_comment_id": comment.id}
```

### 8.6 验证历史 API

```python
@router.get("/tasks/{task_id}/verifications")
async def get_verification_history(task_id: str, db: Session = Depends(get_db)):
    from reins.models.base import TaskComment
    comments = db.query(TaskComment).filter(
        TaskComment.task_id == task_id,
        TaskComment.type.in_(["verification", "human_ruling"])
    ).order_by(TaskComment.created_at.asc()).all()

    result = []
    for c in comments:
        meta = json.loads(c.metadata) if c.metadata else {}
        if c.type == "verification":
            result.append({
                "cycle": meta.get("verification_cycle", 0),
                "type": "verification",
                "verifier": c.author,
                "passed": meta.get("passed"),
                "checks": meta.get("checks", []),
                "body": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None
            })
        else:
            result.append({
                "type": "human_ruling",
                "author": c.author,
                "ruling_action": meta.get("ruling_action"),
                "body": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None
            })
    return result
```

---

## 九、边界情况处理

| 场景 | 处理方式 |
|------|---------|
| Executor 被删除/离线 | 转 disputed，人工重新分配 |
| Verifier 验证超时 | 设 timeout（默认 5 分钟），超时标记 failed |
| 同一任务同时被两个 Worker 领到 | heartbeat 加锁：`WHERE status='review_needed' AND assigned_agent IS NULL` |
| human_ruling 和 verification 同时存在 | human_ruling 优先，Executor 按裁决意见执行 |
| 验证通过后又被人工打回 | 人工可直接改 status + 写 comment，不需要走 verification 流程 |
| verification_cycle 被误设为 >3 | 代码层强制 `min(cycle, MAX_CYCLES)` |

---

## 十、与 Sprint 53 的关系

| Sprint 53（已完成） | Sprint 54（本设计） |
|---------------------|---------------------|
| 三级 verifier 继承链 | 验证结果写 comment |
| DB verifier_agent_id 列 | DB verification_cycle 列 + task_comments 表 |
| complete_task 自动路由 | cycle 计数 + disputed 逻辑 |
| ResultVerifier 基础类 | ResultVerifier 改造（comment + cycle） |
| E2E 42/42 测试 | E2E 新增：循环 + disputed + 裁决 |

**Sprint 54 不改动 Sprint 53 已有功能，只做增量扩展。**

---

## 十一、Sprint 54 任务计划

> 执行顺序：Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
> 每个 Phase 内部任务可并行，Phase 之间必须串行（前一 Phase 完成后才能开始下一 Phase）。

---

### Phase 0: DB 基础（必须先做）

**依赖**：无，第一个执行

#### 任务 0.1: DB 迁移 016 — 创建 task_comments 表 + verification_cycle 列

**文件**：`packages/server/migrations/016_verification_cycle_and_comments.sql`

**内容**：
- `ALTER TABLE tasks ADD COLUMN verification_cycle INT DEFAULT 0`
- `CREATE TABLE task_comments`（id, task_id, author, author_role, type, content, is_agent_reply, metadata, created_at）
- 创建索引：`idx_task_comments_task_id`, `idx_task_comments_type`

**验收标准**：
- [ ] 执行迁移脚本后，`tasks` 表有 `verification_cycle` 列（`PRAGMA table_info(tasks)` 验证）
- [ ] `task_comments` 表存在（`PRAGMA table_info(task_comments)` 验证）
- [ ] 索引已创建（`PRAGMA index_list(task_comments)` 验证）
- [ ] 迁移可重复执行（`CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` 幂等）

---

#### 任务 0.2: TaskComment ORM 模型 + Task Model 更新

**文件**：
- `packages/server/src/reins/models/base.py`（加 TaskComment 类）
- `packages/server/src/reins/models/task.py`（加 `verification_cycle` 列 + `TaskStatus.DISPUTED`）

**内容**：
- 新建 `TaskComment` ORM 类（见 8.1 节代码）
- `Task` 模型加 `verification_cycle = Column(Integer, default=0)`
- `TaskStatus` 加 `DISPUTED = 'disputed'`
- `Task.to_dict()` 加 `verification_cycle` 字段
- `auto_schema` 自动包含新列

**验收标准**：
- [ ] `python -c "from reins.models.base import TaskComment; print(TaskComment)"` 不报错
- [ ] `python -c "from reins.models.task import Task; t = Task(); print(t.verification_cycle)"` 输出 0
- [ ] `TaskStatus.DISPUTED == 'disputed'`
- [ ] `TaskResponse` schema 包含 `verification_cycle` 字段

---

### Phase 1: ResultVerifier 改造 + 新 API（核心后端）

**依赖**：Phase 0 完成

#### 任务 1.1: ResultVerifier 改造 — 验证结果写 comment + cycle + disputed

**文件**：`packages/server/src/reins/scheduler/result_verifier.py`

**内容**：
- `trigger_verification()` 改造：
  - 验证失败 → 写 verification comment → status=review_needed → cycle++
  - cycle >= 3 → 写 disputed comment → status=disputed → 通知人类
  - 验证通过 → 写 verification comment → status=done
- 新增 `_write_verification_comment()` 方法
- 新增 `MAX_VERIFICATION_CYCLES = 3` 常量

**验收标准**：
- [ ] 验证通过 → task_comments 表新增一条 type=verification, passed=true 的记录 → task.status=done
- [ ] 验证失败 cycle=1 → task_comments 表新增一条 type=verification, passed=false 的记录 → task.status=review_needed, verification_cycle=1
- [ ] 验证失败 cycle=3 → task_comments 表新增两条记录（失败结果 + disputed 通知）→ task.status=disputed, verification_cycle=3
- [ ] comment 的 metadata 字段包含 `{"verification_cycle": N, "passed": bool, "checks": [...]}`

---

#### 任务 1.2: 人工裁决 API

**文件**：`packages/server/src/reins/api/tasks.py`

**内容**：
- `POST /api/v1/tasks/{task_id}/ruling` 端点
- 验证 task.status == disputed
- 写入 human_ruling comment
- 根据 action 设置 status（done / in_progress / verifying）

**验收标准**：
- [ ] disputed 任务提交裁决 → 返回 200 + ruling_comment_id
- [ ] task_comments 表新增一条 type=human_ruling 的记录
- [ ] 裁决 action=done → task.status=done, completed_at 设置
- [ ] 裁决 action=in_progress → task.status=in_progress, verification_cycle=0
- [ ] 非 disputed 任务提交裁决 → 返回 400
- [ ] curl 验证：`curl -X POST localhost:8090/api/v1/tasks/test-xxx/ruling -H 'Content-Type: application/json' -d '{"ruling":"通过","action":"done"}'`

---

#### 任务 1.3: 验证历史 API

**文件**：`packages/server/src/reins/api/tasks.py`

**内容**：
- `GET /api/v1/tasks/{task_id}/verifications` 端点
- 查询 task_comments 中 type IN ('verification', 'human_ruling') 的记录
- 按 created_at 升序返回

**验收标准**：
- [ ] 返回 JSON 数组，包含所有验证轮次和裁决记录
- [ ] verification 类型包含 cycle, passed, checks 字段
- [ ] human_ruling 类型包含 ruling_action 字段
- [ ] curl 验证：`curl localhost:8090/api/v1/tasks/test-xxx/verifications` 返回正确结构

---

### Phase 2: 派发 + Worker 改造

**依赖**：Phase 1 完成

#### 任务 2.1: Heartbeat 改造 — 检测 review_needed + 附带 comment 重新派发

**文件**：`packages/server/src/reins/api/assignment.py`（heartbeat 端点内）

**内容**：
- 在 heartbeat 处理中，检测该 agent 的 review_needed 任务
- 优先检查 human_ruling comment（裁决优先）
- 其次检查 verification comment
- 设置任务 status=in_progress，附带 comment ID 或裁决内容
- 在 tasks 表加 `ruling_comment_id`, `ruling_instruction`, `instruction_comment_id` 列（迁移脚本 016b）

**验收标准**：
- [ ] review_needed 任务在下次 heartbeat 时自动变为 in_progress
- [ ] 有人工裁决时，task.ruling_instruction 包含裁决内容
- [ ] 无裁决有验证意见时，task.instruction_comment_id 指向最近的 verification comment
- [ ] curl heartbeat 端点后，task 状态从 review_needed 变为 in_progress
- [ ] 不会重复派发已完成或已 disputed 的任务

---

#### 任务 2.2: Worker 改造 — 领任务时读取 comment

**文件**：`scripts/agent_worker.py`

**内容**：
- `_build_task_prompt()` 改造：
  - 检查 `ruling_instruction` → 附加人类裁决意见
  - 检查 `instruction_comment_id` → 调 API 获取 comment 内容 → 附加验证意见
  - 标记这是"重新派发的任务"

**验收标准**：
- [ ] Worker 领到 review_needed 任务时，prompt 包含验证意见
- [ ] Worker 领到有裁决的任务时，prompt 包含裁决意见
- [ ] 普通任务领到时，prompt 不变（无额外内容）
- [ ] 实际运行 Worker，验证 prompt 内容正确

---

### Phase 3: 前端改造

**依赖**：Phase 2 完成

#### 任务 3.1: 前端 statusMap 更新

**文件**：`packages/server/src/utils/statusMap.ts`

**内容**：
- 新增 `disputed` 状态映射（badge 颜色、图标、中文文案）

**验收标准**：
- [ ] `mapTaskStatus('disputed')` 返回 `{ label: '争议中', color: 'red', icon: '⚠️' }`
- [ ] TypeScript 编译通过（`npx tsc --noEmit` 0 errors）

---

#### 任务 3.2: TaskList/Dashboard 增强

**文件**：
- `packages/server/src/pages/TaskList.tsx`
- `packages/server/src/pages/Dashboard.tsx`

**内容**：
- TaskList 显示 verification_cycle 数（如 "cycle 2/3"）
- Dashboard 新增 disputed 统计卡片
- disputed 任务显示橙色/红色高亮

**验收标准**：
- [ ] 页面能正常渲染（不是白屏）
- [ ] disputed 任务在 TaskList 中显示红色 badge
- [ ] 有 cycle > 0 的任务显示 "cycle N/3"
- [ ] Dashboard 统计卡片显示 disputed 任务数

---

#### 任务 3.3: 裁决 UI + 验证历史面板

**文件**：
- `packages/server/src/pages/TaskDetail.tsx` 或新建组件
- `packages/server/src/api/tasks.ts`

**内容**：
- 新增 `submitRuling(taskId, ruling, action)` API 调用
- 新增 `getVerifications(taskId)` API 调用
- TaskDetail 页面：disputed 任务显示裁决输入框
- TaskDetail 页面：验证历史面板（显示所有轮次）

**验收标准**：
- [ ] disputed 任务详情页显示裁决输入框（文本 + 下拉选择 action）
- [ ] 提交裁决后，任务状态更新，页面刷新
- [ ] 验证历史面板显示所有 verification 和 human_ruling 记录
- [ ] API 调用返回 200 + 正确结构

---

### Phase 4: E2E 集成测试

**依赖**：Phase 3 完成

#### 任务 4.1: E2E 测试 — 完整验证循环 + disputed + 人工裁决

**文件**：`packages/server/temp/test_verification_cycle.py`

**内容**：测试场景（至少 5 个）：

| # | 场景 | 验证点 |
|---|------|--------|
| 1 | 验证通过 → done | comment 写入, status=done, completed_at 设置 |
| 2 | 验证失败 cycle 1 → review_needed | comment 写入, status=review_needed, cycle=1 |
| 3 | 验证失败 cycle 2 → review_needed | comment 写入, cycle=2 |
| 4 | 验证失败 cycle 3 → disputed | comment 写入, status=disputed, cycle=3 |
| 5 | Heartbeat 自动重新派发 | review_needed → in_progress, 附带 comment |
| 6 | 人工裁决 → done | ruling comment 写入, status=done |
| 7 | 人工裁决 → in_progress | status=in_progress, cycle=0, 附带裁决意见 |
| 8 | 验证历史 API | 返回所有轮次，顺序正确 |
| 9 | Worker 读取 comment | prompt 包含验证意见/裁决意见 |
| 10 | 非 disputed 提交裁决 | 返回 400 |

**验收标准**：
- [ ] 所有测试通过（pytest 10/10）
- [ ] 后端重启无错误
- [ ] 前端页面能正常访问

---

### Phase 执行顺序总览

```
Phase 0 (DB 基础)
  ├── 0.1 DB 迁移 016
  └── 0.2 TaskComment ORM + Task Model 更新
        ↓
Phase 1 (后端核心)
  ├── 1.1 ResultVerifier 改造
  ├── 1.2 人工裁决 API
  └── 1.3 验证历史 API
        ↓
Phase 2 (派发 + Worker)
  ├── 2.1 Heartbeat 改造
  └── 2.2 Worker 改造
        ↓
Phase 3 (前端)
  ├── 3.1 statusMap 更新
  ├── 3.2 TaskList/Dashboard 增强
  └── 3.3 裁决 UI + 验证历史面板
        ↓
Phase 4 (E2E 测试)
  └── 4.1 完整 E2E 测试（10 个场景）
```

### 任务汇总表

| Phase | 任务数 | 文件数 | 预估工作量 |
|-------|--------|--------|-----------|
| Phase 0 | 2 | 3 | 小 |
| Phase 1 | 3 | 2 | 中 |
| Phase 2 | 2 | 2 | 中 |
| Phase 3 | 3 | 4 | 大 |
| Phase 4 | 1 | 1 | 中 |
| **总计** | **11** | **12** | — |

---

## 十二、全局验收标准

1. ✅ 验证失败 → task_comments 写入 + status=review_needed
2. ✅ Heartbeat 自动重新派发 review_needed 任务（附带 comment）
3. ✅ Executor 能读到 verification comment 并据此修改
4. ✅ 第 3 次仍失败 → status=disputed
5. ✅ 人工裁决 → Executor 按裁决意见执行
6. ✅ E2E 测试覆盖：正常循环(≤3次) + disputed + 人工裁决
7. ✅ TypeScript 编译通过（0 errors）
8. ✅ 后端重启无错误
9. ✅ 前端页面能正常渲染（不是白屏）

---

<!-- 后续实施记录追加到此文件 -->

## 十二、E2E 测试记录（2026-05-05）

### 测试结果：22 通过 / 8 失败（5月5日 06:52）

**核心业务链路验证通过**：

| # | 场景 | 结果 | 说明 |
|---|------|------|------|
| 1 | 完成任务 → verifying | ✅ | complete_task 返回 200 |
| 2 | 手动触发验证 | ✅ | verify API 返回 200，passed=false → review_needed |
| 3 | verification comment 写入 | ✅ | verifications API 返回 200，有记录 |
| 4 | Cycle 1 → review_needed | ✅ | cycle=1，status=review_needed |
| 5 | 人工裁决 → in_progress | ✅ | ruling API 返回 200，status=in_progress |
| 6 | ruling_instruction 保存 | ✅ | task.ruling_instruction 包含裁决内容 |
| 7 | verification_cycle 重置 | ✅ | 裁决后 cycle=0 |
| 8 | 验证历史 API | ✅ | 返回 7 条记录（6 verification + 1 human_ruling） |
| 9 | 人工裁决 → done | ✅ | ruling API 返回 200，status=done，completed_at 设置 |
| 10 | human_ruling comment 写入 | ✅ | verifications API 包含 human_ruling 记录 |

**发现的 Bug**：

| # | Bug | 严重度 | 说明 |
|---|-----|--------|------|
| 1 | review_needed → complete 返回 500 | 🔴 P0 | DB session 冲突，详见 doc 15 第十节 |
| 2 | verification_cycle 计数多 1（4 而非 3） | 🟡 P1 | 重复递增导致 |
| 3 | heartbeat 不派发 review_needed 任务 | 🔴 P0 | SQL 查询缺 review_needed 状态 |

**Bug 修复状态**（2026-05-05 07:08）:
- 已派发给扣子（kouzi agent）修复 3 个 bug
- 预期修复后 E2E 测试通过率 ≥ 25/27
- 修复前测试脚本: `packages/server/temp/test_human_ruling.py`

### 实施的代码变更

1. DB 迁移 016：添加 verification_cycle、ruling_comment_id、instruction_comment_id、ruling_instruction 列
2. task_comments 表新增 author_role、type、metadata 列
3. ResultVerifier 改造：_write_verification_comment、MAX_VERIFICATION_CYCLES=3、cycle 计数
4. 新增 API：GET /tasks/{id}/verifications、POST /tasks/{id}/ruling
5. Task 模型新增 verification_cycle 等列
6. complete_task 改造：检测 re-dispatch 并立即触发验证
