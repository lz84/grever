---
name: executor
description: 智能体通过心跳领取任务、执行并上报结果。支持任务上下文获取、进度上报、结果提交和失败记录。执行完成时必须填写 context_md（四级必填结构）。
tags: [execution, task, worker, reporting, nexus, context-md]
---

# Executor (行)

任务执行引擎 — 智能体 通过心跳领取任务、执行、上报结果。

## 何时激活

- 智能体 需要领取待执行任务
- 执行任务后需要上报结果
- 任务失败需要记录错误信息
- 需要获取任务上下文和指导

## 命令

```bash
python skill.py claim                  # 领取任务
python skill.py context <task_id>      # 获取任务上下文
python skill.py complete <task_id> --result "Done"  # 上报完成
python skill.py complete <task_id> --result "Done" --duration_ms 2000 --confidence 0.95
python skill.py fail <task_id> --error_type timeout --error_message "Timed out"
python skill.py update <task_id> --status in_progress --progress 50
```

## 执行流程

```
1. 心跳领取（claim）→ 获取 assigned_tasks
2. 读取上下文（context）→ 获取任务详情和历史
3. 执行任务
4. 上报完成（complete）→ 必须填写 context_md → 自动触发验证
5. 验证流程（自动）：
   ├── context_md 为空 + needs_verification=True → ❌ 拒绝完成（400 错误）
   ├── 无验收标准 → status = done ✅
   └── 有验收标准 → status = verifying → Verifier 验证
       ├── 全部通过 → status = done ✅
       └── 不通过 → review_needed / disputed
```

## context_md 填写规则（强制执行）

### 三条铁律

1. **执行时必须写 context_md**：任务完成时 context_md 为空且 needs_verification=True → 拒绝完成（400 错误）。
2. **四级必填结构**：context_md 必须包含以下 4 个小节：

```markdown
### 📝 执行摘要
- 做了什么：[简述核心改动，1-3句话]
- 关键决策：[重要选择及原因，如选择了方案A因为B]
- 已知风险：[遗留问题、TODO 或注意事项]

### 📂 变更文件
- `相对路径/文件名` — 一句话说明改了什么
- `相对路径/文件名` — 新建/修改/删除

### ✅ 验证方法
- 具体命令或步骤，让验证者可以复现你的工作
- 如：`curl http://127.0.0.1:8097/api/v1/health` 返回 200
- 如：`python -m py_compile file.py` 无报错
- 如：DB 检查某个字段有值

### 🔗 相关资源
- 设计文档路径：`docs/xxx.md`
- 相关任务 ID：`task-xxx`
- 相关链接或参考
```

3. **验证者依赖 context_md**：验证者派发路径的 prompt 会自动注入 `### 🧭 执行者上下文` 小节，包含你写的完整 context_md。写得越清晰，验证越快通过。

### context_md 写入方式

通过 complete 命令附带 context_md：

```bash
python skill.py complete <task_id> \
  --result "任务完成" \
  --context_md "### 📝 执行摘要
- 做了什么：...
- 关键决策：...
- 已知风险：...

### 📂 变更文件
- file.py — ...

### ✅ 验证方法
- curl ... 返回 200

### 🔗 相关资源
- docs/xxx.md"
```

或通过 API 直接更新：

```bash
PUT {NEXUS_SERVER_URL}/api/v1/tasks/{id}
{
  "status": "done",
  "context_md": "### 📝 执行摘要\n...\n### 🔗 相关资源\n..."
}
```

### 反面案例（禁止）

```markdown
❌ 空 context_md → 任务拒绝完成
❌ 只写"完成"两个字 → 验证者无法判断
❌ 缺少任一必填小节 → 视为不完整
❌ 写无关内容（如闲聊） → 视为无效
```

### 正面案例（推荐）

```markdown
### 📝 执行摘要
- 做了什么：新增了任务完成时的 context_md 校验，防止空上下文提交
- 关键决策：选择 400 错误而非 422，因为这是业务规则校验失败
- 已知风险：旧任务可能没有 context_md，但不影响已有 done 状态的任务

### 📂 变更文件
- `packages/server/src/reins/api/tasks_crud.py` — 新增 complete 时校验 context_md 逻辑
- `tests/test_tasks_crud.py` — 新增 context_md 校验测试用例

### ✅ 验证方法
- `python -m py_compile tasks_crud.py` — 无报错
- `curl http://127.0.0.1:8097/api/v1/tasks/{id}/complete -X POST -d '{}'` — 返回 400
- `curl ... -d '{"context_md": "test"}'` — 返回 200
- DB 检查：task.status 变为 review_needed，context_md 有值

### 🔗 相关资源
- 设计文档：`docs/sprint-86-three-tier-context.md`
- 前置任务：`task-2963fb12aa45` — context_builder 注入 context_md 到 prompt
```

## 与 Pulse 的关系

Executor 依赖 Pulse 的注册和心跳机制来领取任务。心跳不仅是保活，也是任务分发的触发点。

## 与 Verifier 的关系

Executor 完成任务后，任务进入 `review_needed` 状态，由 Verifier 进行验收。**Verifier 能看到你写的 context_md**，所以写得清晰准确能大幅加快验证速度。
