# Nexus 进化引擎（Evo）详细设计

**版本**: v1.0  
**作者**: 刚子  
**日期**: 2026-06-01  
**状态**: 已完成 Sprint 104（GEP 协议统一）  

---

## 1. 概念定义

### 1.1 什么是进化引擎

**Evo（Evolution）是 Nexus 的进化引擎，负责将 Agent 执行任务的经验转化为可复用的进化规则，并自动更新匹配引擎的权重，让系统在派发任务时越来越聪明。**

一句话：**输入是"过去干过的活"，输出是"下次怎么干更好"。**

### 1.2 核心定位

| 维度 | 说明 |
|------|------|
| **不属于哪个域** | 进化域（Evolution Domain）|
| **上游依赖** | Reins（任务管理）的任务执行结果 |
| **下游消费** | TaskAssigner（任务派发）的匹配引擎 |
| **同级协作** | GrASP（知识注入）提供上下文 |

### 1.3 与 GrASP 的关系

| | GrASP（认知域） | Evo（进化域） |
|---|---|---|
| **管什么** | 文档→知识片段→检索注入 | 执行结果→经验规则→权重更新 |
| **输入** | 外部文档、代码、需求 | 已完成的任务执行记录 |
| **输出** | 检索结果（context）注入任务 prompt | 权重调整（agent_tag_weights）影响派发决策 |
| **类比** | Agent 的"短期记忆" | Agent 的"经验总结" |

---

## 2. 输入：进什么

### 2.1 数据源

进化引擎的唯一数据源是 **Reins 的 tasks 表**，读取已完成的任务记录：

```sql
SELECT id, title, status, assigned_agent, project_id,
       capability_tags, created_at, completed_at,
       error_type, error_message, result_summary
FROM tasks
WHERE status IN ('done', 'failed', 'error', 'timeout')
  AND completed_at >= :cutoff
```

### 2.2 输入字段映射

| DB 字段 | 蒸馏用途 | 示例 |
|---------|---------|------|
| `id` | 溯源，记录基因的来源任务 | "task-xxx" |
| `status` | 判断成功/失败 | "done"→成功，"failed"→失败 |
| `assigned_agent` | 分析哪个 Agent 适合什么任务 | "876b9322-..." |
| `capability_tags` | 任务需要哪些能力 | {"technical":["coding","api"]} |
| `completed_at` - `created_at` | 计算执行时长 | 120000ms |
| `error_type` | 分析失败模式 | "user_reported" |
| `result_summary` | 提取经验摘要 | "成功修复了分页逻辑" |

### 2.3 关联数据

蒸馏时还会从 `agents` 表读取 Agent 的能力配置：

```sql
SELECT id, capability_tags FROM agents
```

用于分析"哪些 Agent 能力组合导致了成功"。

### 2.4 输入规模

当前 Nexus 有 **177 个已完成任务**，分布在：
- 147 个成功（done）
- 10 个失败（failed/error/timeout）

---

## 3. 处理：怎么进化

### 3.1 整体流程

```
┌───────────────────────────────────────────────────────────────┐
│                    Evo 进化引擎                                │
│                                                               │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│  │  蒸馏    │ ──→ │  固化    │ ──→ │  权重更新 │              │
│  │Distiller │     │Solidifier│     │WeightUpdater│            │
│  └──────────┘     └──────────┘     └──────────┘              │
│       ↓                ↓                ↓                     │
│   List[Gene]     List[Capsule]    List[EvolutionEvent]        │
│   (基因)         (记忆体)         (进化事件)                   │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 第一阶段：蒸馏（Distiller）

**职责**：从任务记录中提取 6 类基因（Gene）。

#### 3.2.1 能力基因（Capability Gene）

**提取逻辑**：按任务类型+状态分组，统计成功任务中 Agent 的能力出现频率。

```
输入：118 个成功任务
分析：这些任务的 Agent 都有什么能力？
输出：Gene(category="capability")
  → "成功任务的 Agent 通常具备 coding 能力"
```

#### 3.2.2 模式基因（Pattern Gene）

**提取逻辑**：分析成功任务的共同特征（质量分数分布、执行时长基准）。

```
输入：147 个成功任务
分析：平均质量分数 0.80，平均执行时长 45000ms
输出：Gene(category="pattern")
  → "高质量任务平均质量 0.80"
  → "成功任务平均执行时长 45000ms"
```

#### 3.2.3 反模式基因（Anti-Pattern Gene）

**提取逻辑**：分析失败任务的共同错误类型。

```
输入：9 个失败任务
分析：错误类型分布 → user_reported 出现 9 次
输出：Gene(category="anti_pattern")
  → "user_reported 错误出现 9 次，需要避免"
```

#### 3.2.4 序列基因（Sequence Gene）

**提取逻辑**：按项目分组，按完成时间排序，提取任务执行顺序。

```
输入：项目 A 的 5 个已完成任务
分析：调研→设计→编码→测试→部署
输出：Gene(category="sequence")
  → "项目 A 的任务执行顺序：调研→设计→编码→测试→部署"
```

#### 3.2.5 条件基因 & 约束基因

**提取逻辑**：从任务前置条件、依赖关系中提取执行条件和约束。

### 3.3 第二阶段：固化（Solidifier）

**职责**：将蒸馏出的基因过滤、去重、合并，固化为记忆体（Capsule）。

#### 3.3.1 质量过滤

| 规则 | 阈值 | 结果 |
|------|------|------|
| 置信度 < 0.6 且非反模式 | 淘汰 | 大多数低支持度基因被过滤 |
| 支持案例数 < 3 | 淘汰 | 只有 1-2 次观察的不固化 |
| 反模式 | 阈值减半（置信度≥0.4，支持≥1）| 安全优先，尽早记录 |

#### 3.3.2 去重与合并

- **去重**：计算基因指纹（条件+动作+类型的 MD5），相同指纹只保留一个
- **合并**：相似基因（条件重叠≥80%）合并，置信度取平均值，支持案例数累加

#### 3.3.3 状态分级

| 状态 | 置信度范围 | 含义 |
|------|-----------|------|
| **SOLIDIFIED** | ≥ 0.8 | 正式使用，影响派发决策 |
| **VALIDATED** | 0.6 ~ 0.8 | 可试用，轻量影响 |
| **DRAFT** | < 0.6 | 草稿，观察中 |
| **DEPRECATED** | — | 已废弃，不再影响 |

### 3.4 第三阶段：权重更新（WeightUpdater）

**职责**：将固化记忆体的权重调整应用到 `agent_tag_weights` 表。

#### 3.4.1 权重调整逻辑

```python
# 从 Capsule 的 weight_adjustments 提取
for tag, delta in capsule.weight_adjustments.items():
    old_weight = 1.0  # 默认
    new_weight = old_weight + delta  # 通常 +0.1
    
    # 更新 agent_tag_weights 表
    UPDATE agent_tag_weights SET weight = ? 
    WHERE agent_id = ? AND tag = ?
```

#### 3.4.2 权重来源

| Capsule 类型 | 权重调整方式 |
|-------------|-------------|
| **能力基因** → 推荐的能力 +0.1 | 蒸馏发现某能力与成功高度相关 |
| **模式基因** → 无直接权重 | 记录基准值，用于后续验证 |
| **反模式基因** → 相关能力 -0.1 | 蒸馏发现某能力与失败高度相关 |

---

## 4. 输出：出什么

### 4.1 三类输出物

#### 输出 1：Gene（基因）

**存什么**：`genes` 表  
**是什么**：可复用的经验规则

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 基因 ID | "gene-0001" |
| `category` | 类型 | "capability" / "pattern" / "anti_pattern" / "sequence" |
| `signals_match` | 触发信号 | ["task_type:coding"] |
| `strategy` | 策略步骤 | [{"action":"recommend","value":["coding"]}] |
| `constraints` | 约束条件 | {"max_files": 10} |
| `epigenetic_marks` | 表观遗传标记 | [{"mark":"score","value":0.76}] |

#### 输出 2：Capsule（记忆体）

**存什么**：`capsules` 表  
**是什么**：固化后的经验证据

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 记忆体 ID | "capsule-0001" |
| `gene_id` | 关联基因 | "gene-0001" |
| `summary` | 经验摘要 | "成功任务 Agent 通常具备 coding 能力" |
| `confidence` | 置信度 | 0.76 |
| `outcome` | 结果 | {"status":"success","score":0.76} |
| `a2a` | A2A 共享属性 | {"source":"local","ready_for_hub":false} |

#### 输出 3：EvolutionEvent（进化事件）

**存什么**：`evolution_events` 表  
**是什么**：权重变更的审计日志

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 事件 ID | "evo-000001" |
| `intent` | 意图 | "optimize" |
| `capsule_id` | 关联记忆体 | "capsule-0001" |
| `outcome` | 变更结果 | {"status":"applied"} |
| `meta` | 元数据 | {"source":"capsule-0001"} |

### 4.2 最终生效产物

**进化引擎的最终生效产物是 `agent_tag_weights` 表**：

| agent_id | tag | weight | last_observed |
|----------|-----|--------|---------------|
| 刚子 | coding | 1.1 | 2026-06-01 |
| 谷子 | coding | 1.1 | 2026-06-01 |
| 麻子 | coding | 1.1 | 2026-06-01 |
| ... | ... | ... | ... |

**这就是匹配引擎真正查的表**。蒸馏不直接决定派给谁，而是通过更新权重来间接影响决策。

---

## 5. 其他模块怎么利用成果

### 5.1 TaskAssigner（任务派发）→ 匹配引擎

**使用方式**：派发任务时读取 `agent_tag_weights` 表计算匹配分数。

```python
# agent_matcher.py 的核心逻辑
def match_for_task(task_capability_tags):
    """
    1. 查在线 Agent
    2. 对每个 Agent：
       a. 查 agent_tag_weights → 获取该 Agent 每个 tag 的权重
       b. 计算匹配分数 = Σ(匹配 tag 的 weight) / 需要的 tag 总数
    3. 按分数降序排列，选最高分的
    """
    weights = _get_agent_weights(agent["id"])  # ← 读 agent_tag_weights 表
    score = sum(weights.get(t, 1.0) for t in matched) / len(required)
```

**进化前后的变化**：

```
进化前（权重都是默认 1.0）：
  数据分析任务需要 [sql, python]
  麻子：sql(1.0) + python(1.0) = 2.0 → 分数 1.0
  谷子：sql(1.0) + python(1.0) = 2.0 → 分数 1.0
  → 分数一样，按负载选（纯随机）

进化后（蒸馏发现 coding 能力与成功高度相关）：
  麻子：sql(1.0) + python(1.0) = 2.0 → 分数 1.0
  谷子：sql(1.1) + python(1.1) = 2.2 → 分数 1.1  ← 权重高了
  → 谷子优先被选中
```

### 5.2 GrASP（认知域）→ 知识注入

**使用方式**：未来可读取 Capsule 的 summary 作为最佳实践注入任务上下文。

```python
# 未来接入点
def enrich_task_context(task):
    """将相关 Capsule 的经验注入任务 context"""
    capsules = get_related_capsules(task.capability_tags)
    context_md = build_context_md(capsules)
    return context_md
```

**示例**：任务需要 coding 能力时，自动注入"成功任务的 Agent 通常具备 coding 能力"这条经验。

### 5.3 Vigil（安全域）→ 反模式预警

**使用方式**：读取 anti_pattern 类型的 Capsule，对高风险任务提前预警。

```python
# 未来接入点
def check_anti_patterns(task):
    """检查任务是否命中已知的反模式"""
    anti_patterns = get_anti_pattern_capsules()
    for ap in anti_patterns:
        if matches(task, ap):
            return f"⚠️ 此任务命中反模式: {ap.summary}"
    return None
```

### 5.4 前端（仪表盘）→ 进化可视化

**未来可展示**：
- 进化了多少 Gene / Capsule
- 哪些权重被调整了
- 进化事件的时间线
- Capsule 的 success_rate 变化曲线

---

## 6. 触发机制

### 6.1 当前：手动触发

```bash
cd packages/server/src
python -m evo.trigger_distill --lookback 365
```

### 6.2 未来：自动触发

| 触发方式 | 条件 | 频率 |
|---------|------|------|
| **任务完成事件** | 每完成 10 个任务 | 实时 |
| **定时任务** | 每天凌晨 2 点 | 每天 |
| **手动触发** | 用户点击按钮 | 随时 |

### 6.3 触发逻辑（伪代码）

```python
async def on_task_completed(task_id):
    """任务完成后的进化检查"""
    # 检查是否需要触发蒸馏
    pending_count = get_pending_task_count()
    if pending_count >= 10:
        await run_distillation(lookback_days=90)

async def scheduled_distillation():
    """定时蒸馏"""
    await run_distillation(lookback_days=7)  # 只看最近 7 天
```

---

## 7. 数据流全景

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nexus 进化闭环                            │
│                                                                  │
│  ┌──────────────┐                                              │
│  │  Reins 任务   │                                              │
│  │  执行结果     │                                              │
│  │  (tasks 表)   │                                              │
│  └──────┬───────┘                                              │
│         │ SELECT 已完成任务                                       │
│         ▼                                                       │
│  ┌──────────────┐     ┌──────────┐     ┌──────────┐            │
│  │  蒸馏        │ ──→ │  固化    │ ──→ │  权重更新 │            │
│  │  Distiller   │     │Solidifier│     │WeightUpdater│          │
│  └──────┬───────┘     └─────┬────┘     └──────┬────┘            │
│         │                   │                 │                 │
│         ▼                   ▼                 ▼                 │
│    genes 表           capsules 表      agent_tag_weights 表     │
│    (37 个)            (4 个)          (权重被更新)              │
│                                         │                       │
│                                         │ 读权重                 │
│                                         ▼                       │
│                              ┌──────────────────┐              │
│                              │  TaskAssigner    │              │
│                              │  匹配引擎         │              │
│                              │  (agent_matcher) │              │
│                              └──────────────────┘              │
│                                         │                       │
│                                         │ 派发决策               │
│                                         ▼                       │
│                              ┌──────────────────┘              │
│                              │                                 │
│                              ▼                                 │
│  ┌──────────────┐     ┌──────────────┐                        │
│  │  新任务执行   │ ──→ │  新的执行结果 │                        │
│  │  (权重影响)   │     │  (回到 tasks) │                        │
│  └──────────────┘     └──────────────┘                        │
│                                                                  │
│  ─────────── 闭环循环 ───────────                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. 当前状态（Sprint 104 完成后）

### 8.1 已完成

| 项目 | 状态 |
|------|------|
| GEP 协议 dataclass（Gene/Capsule/EvolutionEvent） | ✅ |
| 蒸馏触发器（trigger_distill.py） | ✅ |
| 3 张 GEP 表（genes/capsules/evolution_events） | ✅ |
| 权重更新器（weight_updater.py）适配 GEP | ✅ |
| 首次蒸馏跑通（156 条→37 Gene→4 Capsule→9 权重更新） | ✅ |
| 测试覆盖（54 passed） | ✅ |
| 设计文档（本文档） | ✅ |

### 8.2 未完成

| 项目 | 优先级 | 说明 |
|------|--------|------|
| 自动触发机制 | P1 | 任务完成事件 / 定时任务 |
| Capsule 状态管理 API | P1 | promote / deprecate |
| 进化事件回滚 | P2 | revert_event |
| GrASP 注入 Capsule 经验 | P2 | enrich_task_context |
| Vigil 读取反模式预警 | P2 | check_anti_patterns |
| 前端进化仪表盘 | P3 | 可视化 |
| A2A Hub 技能共享 | P3 | 跨 Agent 分享 Capsule |

---

## 9. 关键设计决策

| 编号 | 决策 | 理由 |
|------|------|------|
| E1 | 进化引擎只读 tasks 表，不写 tasks | 职责分离，进化不干预执行 |
| E2 | 权重调整只影响 agent_tag_weights | 匹配引擎已有读取逻辑，零侵入 |
| E3 | Gene/Capsule/Event 三表分离 | 可追溯：什么规则 → 什么证据 → 什么变更 |
| E4 | 反模式阈值减半 | 安全优先，尽早记录失败模式 |
| E5 | 权重默认值 1.0 | 无进化数据时退化为均匀匹配 |
| E6 | 蒸馏不直接决定派发 | 只更新权重，决策权留给匹配引擎 |

---

*文档结束*
