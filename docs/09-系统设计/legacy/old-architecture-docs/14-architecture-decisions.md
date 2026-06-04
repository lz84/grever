# 架构讨论记录

> 记录所有架构决策、方案对比、取舍理由。后续讨论持续追加。

---

## 2026-05-04: Verifier Agent 三级验证机制

### 背景

Sprint 50-52 质量问题暴露出一个核心缺陷：任务完成后没有独立的验收环节。执行者"自己做、自己验、自己报 done"= 运动员兼裁判，永远有盲区。

### 决策：引入独立 Verifier Agent

用户提出：每个任务由专门的 Agent 去检查结果，而不是执行者自检。

### 设计

**三级继承链**：Goal → Project → Task，每级都可以设置检查 Agent，子级优先于父级。

```
Task.verifier_agent_id → Project.verifier_agent_id → Goal.verifier_agent_id → kouzi(默认)
```

**业务流**：
```
Executor Agent 执行 → 报完成
    → complete_task API 检测 acceptance_criteria
    → 有 → status=verifying，等 ResultVerifier 检查
    → 无 → status=done，直接完成
```

**ResultVerifier 检查类型**：compile / api / page / custom

### 结果

- Sprint 53 完成，42/42 E2E 测试通过
- 三个 commit：`11dd668`（基础设施）、`d5e82a2`（schema/ORM 修复）、`7dec169`（合并 schemas/ 到 models/）

### 教训：双模型层导致数据丢失

发现 `acceptance_criteria` 从 API 写入后 DB 为 NULL。根因：

```
reins/models/task.py    ← ORM 定义了 acceptance_criteria 列 ✅
reins/schemas/task.py   ← Pydantic schema 没定义这个字段 ❌
→ FastAPI 用 schema 解析请求 → 字段被丢弃 → ORM 拿不到 → DB NULL
```

两套独立维护同一实体的字段定义，加字段时必须两边同步，漏一边就数据丢失。

### 决策：合并 schemas/ 到 models/（单源模型）

用 `schema_factory.py` 的 `auto_schema()` 从 SQLAlchemy ORM 列定义自动生成 Pydantic Create/Update/Response。

```
加一个 ORM 列 → API schema 自动同步 → 不会再漏字段
```

- 删除 `schemas/` 目录（11 个文件）
- Task/Goal/Project 用自动推导
- Scenario/Security 复杂嵌套模型保留手动定义，统一放在 models/ 里

---

## 2026-05-04: Human-in-the-Loop（人在环路）

### 背景

用户提出场景：Agent 执行应急演练任务时，需要人类现场报告才能决定下一步流程。

### 核心矛盾

Agent 执行是同步的（一次调用执行完），但人类输入是异步的（可能几分钟甚至几小时后才来）。不能阻塞 Agent session 等待。

### 方案对比

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|------|------|------|------|------|
| 阻塞等待 | Agent 轮询 DB 等人类输入 | 简单 | 浪费资源、session 超时断开 | ❌ |
| 任务拆分 | 等待人类输入 = 独立任务状态，不阻塞 Agent | 不阻塞、下游自动触发 | 需要新的任务状态和 API | ✅ 推荐 |
| 回调机制 | Agent 声明需要输入 → 系统创建输入请求 → 人类提交 → 回调继续 | 灵活 | 实现复杂 | ✅ 结合 |

### 最终设计：方案 2 + 3 结合

**Task Status 扩展**：
```
in_progress → waiting_human → (人类提交) → done → 下游任务自动解锁
```

**Human Input API**：
```
POST /tasks/{id}/human-input
{
  "input_type": "field_report",
  "content": { ... },
  "submitted_by": "user_id"
}
```

### 讨论：是否需要动态表单

用户问：如何应对 Agent 想要的各种字段类型？需要生成动态表单吗？

**结论：不要纯动态表单，用三步递进**

| 层级 | 覆盖 | 方案 | 例子 |
|------|------|------|------|
| 场景模板驱动 | 80% | 场景模板里预定义 human_input_schema | 泄漏等级、影响范围、伤亡人数 |
| Agent 运行时声明 | 15% | Agent 在 result 中标记字段 schema | 天气、风向 |
| 自由文本兜底 | 5% | 一个文本框，LLM 后续提取 | "现场有没有人受伤" |

**不选纯动态表单的理由**：
1. 字段类型爆炸（几十种组件要支持）
2. 校验逻辑复杂（联动、依赖）
3. 维护成本高（Agent 随意要字段，前端永远跟不上）
4. 用户认知负担（每次表单长得不一样）

**原则**：80% 预定义模板 + 20% 自由文本兜底。动态表单只支持 text/number/select 三种基础类型。

### 待讨论（未决策）

- [ ] `waiting_human` 状态的实现细节（是独立状态还是 Task 属性）
- [ ] 通知机制（飞书消息、邮件等）
- [ ] 人类输入是否走 Verifier 检查
- [ ] 超时处理（人类多久没提交算超时）

---

<!-- 后续讨论持续追加到此处 -->

---

## 2026-05-04: Sprint 54 Human-in-the-Loop 计划已创建

用户确认 Human-in-the-Loop 方案，要求在 Nexus 中创建任务执行。

### Sprint 54 任务清单

| Task ID | 标题 | 状态 |
|---------|------|------|
| task-bf8fc4616a56 | T1: DB migration - waiting_human + human_input_requests | todo |
| task-48acb08aac09 | T2: HumanInputRequest ORM model + auto schema | todo |
| task-b0f2d501784a | T3: Agent output parser - needs_human_input detection | todo |
| task-5535e5e116ad | T4: complete_task integration | todo |
| task-05d53d400daa | T5: API endpoints | todo |
| task-9735f885e656 | T6: DependencyResolver extension | todo |
| task-7ee5dbddeb6f | T7: E2E test | todo |

### 设计文档

完整方案在 `docs/sprint-54-human-input-plan.md`
