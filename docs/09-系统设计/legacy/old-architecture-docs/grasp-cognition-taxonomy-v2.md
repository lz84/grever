# Grasp 认知类型体系

**版本**: v0.2
**日期**: 2026-04-07
**参与者**: 用户 + 刚子 + 谷子（CFO 评审）
**状态**: 已评审，待落地

---

## 一、前提条件

### 1.1 Grasp 的定位

Grasp（悟）是 Nexus 平台的**认知层**，核心职责是：

> 领域本体建模、基础认知输出、认知共享与更新

**核心信念**（来自 nexus-vision.md）：

- 智能体不好用的根因是**认知**，不是记忆
- 认知不是一次性装好的静态配置，而是**在使用中持续生长的活体**
- Grasp 提供基础认知让智能体起步就好用，智能体工作中产生的新认知反哺 Grasp，形成**认知共同体**

### 1.2 构建的是智能体认知库，不是传统知识库

| 维度 | 传统知识库 | 智能体认知库 |
|------|-----------|-------------|
| 目的 | 人类理解 | 智能体行动 |
| 内容 | 世界是什么样的 | 我应该做什么、怎么做 |
| 关系 | 上下位(isa) | 因果(enables/requires/produces) |
| 组织方式 | 语义层级分类 | 决策流程驱动 |
| 检索逻辑 | 关键词匹配 | 当前状态→应该调哪个能力 |

### 1.3 本体论基础

以标准本体论（BFO / SUMO）为理论依据：

| 本体论概念 | 含义 |
|-----------|------|
| **Class / Concept** | 事物的类型 |
| **Instance** | 事物的具体个体 |
| **Relation** | 事物之间的联系 |
| **Property / Attribute** | 事物的特征 |
| **State** | 事物的动态快照 |
| **Process / Event** | 发生的事 |

### 1.4 重要设计原则

1. **属性不是独立类型**：Cost、Priority、Risk 是 Goal / Plan / Action 的**可挂载属性**，不是独立认知类型。避免认知库膨胀。
2. **Belief 是置信度标记**：所有 Attribute 默认有 `confidence` 字段（0-1），低于阈值时智能体需保守处理，不需要单独建类型。
3. **Relation 是关系，不是节点**：关系是边，Entity 是节点，一起构成图结构。
4. **闭环优先**：目标导向链必须能从 Effect 反向验证 Goal 是否达成。

---

## 二、认知类型体系

### 2.1 世界结构层

| 类型 | 本体论映射 | 定义 | 例子 |
|------|-----------|------|------|
| **Entity** | Class / Concept | 领域中的关键类型/概念 | "GPU"、"vLLM"、"项目" |
| **Instance** | Instance | Entity 的具体个体，智能体的操作对象 | "DGX-1 上的 GPU #0"、"运行中的 vLLM 服务实例" |
| **Attribute** | Property | 实体的静态特征（可带 `confidence` 置信度） | "GPU 有显存 80GB"、"vLLM 支持 FP8（confidence: 0.85）" |

### 2.2 关系层

| 类型 | 定义 | 例子 |
|------|------|------|
| **Relation** | Entity / Instance 之间的类型化关系，边 | "GPU 支持 CUDA"、"任务 属于 项目"、"vLLM 部署在 GPU 上" |

**Relation 的属性**：
- `source` — 源节点
- `target` — 目标节点
- `type` — 关系类型（如：supports、belongs_to、deployed_on）
- `confidence` — 置信度（0-1）

### 2.3 动态状态层

| 类型 | 定义 | 例子 |
|------|------|------|
| **State** | 某一时间点的快照，静态视图 | "GPU 显存：87% used"、"服务状态：Running" |

**State vs Effect 的区分**：
- **State** = "GPU 显存 87%"（时间点快照）
- **Effect** = "GPU 显存从 80% 增长到 87%，消耗 7%"（变化过程 + 结果）

### 2.4 目标导向链

贯穿 **Intent → Goal → Plan → Task → Action → Effect** 链条，Effect 反向验证 Goal 是否达成。

| 类型 | 定义 | 例子 |
|------|------|------|
| **Intent** | 用户/智能体的根本目的 | "我想让模型在 GPU 上跑起来" |
| **Goal** | Intent 的具体化，可达成的目标状态 | "在 DGX Spark 上部署 vLLM 服务" |
| **Plan** | 为达成 Goal 制定的行动序列 | "申请 GPU → 下载模型 → 配置参数 → 启动服务" |
| **Task** | Plan 中的可执行单元 | "下载 vLLM 模型权重" |
| **Action** | 具体执行动作 | "执行 docker run 命令" |
| **Effect** | Action 产生的变化过程 + 结果，用于验证 Goal | "服务状态从 Stopped 变为 Running（成功）"、"服务启动失败，错误码 137" |

**可挂载属性**（不是独立类型，是 Goal / Plan / Action 的属性）：

| 属性 | 可挂载到 | 定义 | 例子 |
|------|---------|------|------|
| **Cost** | Goal / Plan | 资源/时间/机会成本 | GPU 型号 A 比 B 贵 3 倍 |
| **Priority** | Goal | 任务优先级 | "比用户其他需求更重要" |
| **Risk** | Action | 失败概率 + 影响程度 | "有 20% 概率超时，失败回滚需 2 分钟" |

### 2.5 能力层

| 类型 | 定义 | 例子 |
|------|------|------|
| **Capability** | 某实体能执行某动作的潜能 | "这个工具能处理文件压缩"、"OpenClaw Agent 能执行 shell" |
| **Interface** | Capability 的调用方式 | "POST /api/run，参数是 JSON" |

**Capability 的核心属性**（必须定义，否则智能体只能"看名称"）：

| 属性 | 定义 | 例子 |
|------|------|------|
| 适用场景 | 在什么环境下可用 | "仅支持 Linux 环境" |
| 前置条件 | 调用前必须满足的条件 | "需要 20GB 磁盘空间" |
| 失败模式 | 常见失败原因 | "网络超时、权限不足" |
| 输入输出 | Interface 的格式定义 | 见 Interface |

### 2.6 规范层

| 类型 | 定义 | 例子 |
|------|------|------|
| **Norm** | 不变的安全/业务红线（无 Else 分支） | "密钥不能明文存储"、"删除操作需要二次确认" |
| **Constraint** | 条件性约束，含 If → Then 逻辑 | "如果 操作对象=生产环境 → 禁止 直接删除" |

**Constraint 的完整属性**：

| 属性 | 定义 |
|------|------|
| condition | 触发条件（If） |
| action | 允许/禁止的动作（Then） |
| else_branch | Else 分支（建议补充，如"测试环境可直接删除"） |
| priority | 优先级（多 Constraint 冲突时的执行规则） |

### 2.7 复用层

| 类型 | 定义 | 例子 |
|------|------|------|
| **Pattern** | 反复出现的条件触发行为模式（If-Then） | "遇到 timeout → 等 2 秒 → 重试 → 最多 3 次 → 还失败就报 error" |
| **Template** | 可直接复用的标准化执行单元（带占位符） | "vLLM 部署 SOP"、"docker run 标准参数模板" |

**Pattern vs Template 的区分**：

| | Pattern | Template |
|--|---------|---------|
| 本质 | 条件触发的**行为序列** | 固定参数的可执行**单元** |
| 触发 | If-Then 条件 | 直接调用 |
| 内容 | 含判断和分支 | 含占位符和参数 |
| 例子 | timeout→重试→3次失败→报错 | `docker run --gpus all -v $MODEL_PATH:$CONTAINER_PATH ...` |

### 2.8 信念与评估层

| 类型 | 定义 | 例子 |
|------|------|------|
| **Expectation** | 对未来状态的预测（带置信度） | "预计服务启动需要 3-5 分钟（confidence: 0.8）" |

**Belief 的处理方式**：不作为独立类型，而是所有 Attribute 自带的 `confidence` 字段。
- "vLLM 支持 FP8（confidence: 0.85）" → 置信度 > 阈值，正常使用
- "vLLM 支持 FP8（confidence: 0.4）" → 置信度低，智能体需准备 fallback

**Metric（衡量标准）**：作为 Goal / Plan / Norm 等类型的**挂载属性**，不是独立类型。
- "部署成功率 ≥ 95%" → Metric，挂载在 Goal "部署 vLLM" 上
- "响应时间 P99 < 500ms" → Metric，挂载在 Norm / Plan 上

---

## 三、完整类型一览

| 序号 | 类型 | 层级 | 是节点还是边？ |
|------|------|------|-------------|
| 1 | Entity | 世界结构 | 节点 |
| 2 | Instance | 世界结构 | 节点 |
| 3 | Attribute | 世界结构 | 节点的属性 |
| 4 | Relation | 关系 | 边 |
| 5 | State | 动态状态 | 快照（可作为节点或关系属性） |
| 6 | Intent | 目标导向 | 节点 |
| 7 | Goal | 目标导向 | 节点 |
| 8 | Plan | 目标导向 | 节点 |
| 9 | Task | 目标导向 | 节点 |
| 10 | Action | 目标导向 | 节点 |
| 11 | Effect | 目标导向 | 节点/边 |
| 12 | Capability | 能力 | 节点 |
| 13 | Interface | 能力 | 节点 |
| 14 | Norm | 规范 | 节点 |
| 15 | Constraint | 规范 | 节点 |
| 16 | Pattern | 复用 | 节点 |
| 17 | Template | 复用 | 节点 |
| 18 | Expectation | 信念/评估 | 节点 |

**GraphRAG 可用节点类型**（对应 extract_graph.entity_types）：

```
Entity, Instance, Intent, Goal, Plan, Task, Action, Effect,
Capability, Interface, Norm, Constraint, Pattern, Template, Expectation
```

---

## 四、类型关系图

```
                         ┌─────────────────────────────────────────┐
                         │            世界结构层                    │
                         │   Entity ←──Relation──→ Entity         │
                         │       ↓                  ↓             │
                         │   Instance            Attribute         │
                         │   (具体个体)         (可带confidence)  │
                         └─────────────────────────────────────────┘
                                             ↑
                         ┌───────────────────┴───────────────────┐
                         │            动态状态层                    │
                         │   State（时间点快照）  Effect（变化过程+结果）│
                         └─────────────────────────────────────────┘
                                             ↑
                         ┌───────────────────┴───────────────────┐
                         │            目标导向链                    │
Intent ──→ Goal ──→ Plan ──→ Task ──→ Action ──→ Effect ──┐
                                                              ↓
                                                    Goal 达成验证
    ↕ 可挂载属性：Cost / Priority / Risk
                         └───────────────────┬───────────────────┘
                                             ↑
                         ┌───────────────────┴───────────────────┐
                         │            能力层                      │
                         │   Capability ←──→ Interface         │
                         │   (含:适用场景/前置条件/失败模式)       │
                         └───────────────────────────────────────┘
                                             ↑
                         ┌───────────────────┴───────────────────┐
                         │            规范层                      │
                         │   Norm（不变红线）  Constraint(If→Then) │
                         └───────────────────────────────────────┘
                                             ↑
                         ┌───────────────────┴───────────────────┐
                         │            复用层                      │
                         │   Pattern（条件触发）←→ Template     │
                         │   （可反哺）            （可优化）     │
                         │            ↑                          │
                         │          Metric（衡量标准，可挂载）       │
                         └───────────────────────────────────────┘
                                             ↑
                         ┌───────────────────┴───────────────────┐
                         │          信念/评估层                    │
                         │   Expectation（预测）  Attribute.confidence│
                         └───────────────────────────────────────┘
```

---

## 五、与五兄弟的对应

| 兄弟 | 核心使用的认知类型 |
|------|------------------|
| **悟 Grasp** | 定义和维护所有类型：Entity、Instance、Attribute、Relation、State、Norm、Constraint、Pattern、Template、Capability、Interface、Expectation |
| **御 Reins** | Intent、Goal、Plan、Task、Action、Effect（目标链）；可挂载 Cost/Priority/Risk |
| **达 Reach** | Capability、Interface、Template（能力调用） |
| **化 Evo** | Pattern、Effect、Expectation（经验提炼）；Belief→Attribute 置信度升级 |
| **鉴 Vigil** | Norm、Constraint（执行前拦截）；Metric（安全/质量基准挂载） |

---

## 六、认知更新规则（v0.2 新增）

### 6.1 各类型更新触发条件

| 类型 | 更新触发 | 来源 |
|------|---------|------|
| Entity / Instance | 领域出现新概念/新个体 | 文档注入 / Evo 提炼 |
| Attribute | 置信度发生变化（验证/推翻） | Evo 验证 / Reach 执行反馈 |
| Relation | 新关联被发现 | 文档注入 / 推理发现 |
| State | 状态快照更新 | Reach 执行后上报 |
| Pattern | Action + Effect 序列重复出现 ≥ 3 次 | Evo 分析执行历史 |
| Template | Pattern 验证成功 ≥ 5 次，固化 | Evo solidify |
| Belief(confidence) | 置信度达到阈值（如 ≥ 0.95） | 验证通过，转为 Attribute |
| Norm / Constraint | 人工审核确认 | Vigil 安全审查 |
| Capability / Interface | 新能力被发现/注册 | Reach 能力画像上报 |

### 6.2 置信度升级规则

Belief（置信度 < 1 的 Attribute）升级为正式 Attribute 的条件：

1. **Evo 验证**：相同场景下成功 ≥ 5 次
2. **无反例**：连续 10 次执行无失败
3. **来源可靠**：来源实体验证或权威文档

---

## 七、待落地问题（v0.2 仍待解决）

1. **Constraint 的 Else 分支和优先级**：多 Constraint 冲突时执行规则未细化
2. **Effect 的完整建模**：负面 Effect（失败）和正面 Effect（成功）的统一表示
3. **五兄弟认知流转的接口规范**：Grasp 与其他兄弟的数据交换格式（另写接口文档）

---

*本文档是讨论稿，经评审后形成正式版本。*
