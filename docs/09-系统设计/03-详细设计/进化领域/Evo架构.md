# Nexus 智能体协同驾驭平台 - 化（Evo）架构设计

**版本**: v1.5  
**作者**: 麻子  
**最后更新**: 2026-06-01 14:00  

---

## 1. 概述

**Evo（化）** 是 Nexus 平台的**能力进化引擎**，基于 GEP（Genome Evolution Protocol，基因组进化协议）实现 Agent 的自进化能力。

**核心定位**:
- 从 Agent 执行经验中自动提取和固化技能
- 通过基因变异和选择实现策略优化
- 构建可复用、可分享的技能库

**设计理念**:
- **生物进化启发**：模仿 DNA 的复制、变异、选择、固化机制
- **经验驱动**：从成功/失败案例中学习，而非人工规则
- **闭环进化**：收集→分析→变异→执行→固化→共享 的完整闭环

### 1.1 参考基准

**主要参考**:
- **@evomap/evolver npm 包**: GEP 协议的核心实现，Nexus Evo 的架构蓝本（位于 `E:\openclaw-workspace\.openclaw\workspace\node_modules\@evomap\evolver`）
- **Kubeflow Pipelines**: ML 工作流（参考其实验追踪）
- **OpenAPI 3.0**: RESTful 接口规范

**与 MLOps 工具的本质差异**:

| 维度 | MLflow/Kubeflow | Nexus Evo |
|------|-----------------|-----------|
| 进化对象 | 机器学习模型 | AI Agent 行为策略 |
| 经验来源 | 训练数据集 | Agent 实际执行任务 |
| 进化机制 | 梯度下降/超参调整 | GEP 基因变异 + 表型表达 |
| 知识单元 | 模型权重 | Gene（基因）+ Capsule（记忆体） |
| 共享方式 | 模型注册表 | A2A Hub 技能分享 |
| 进化粒度 | 训练作业级 | Agent 任务级/技能级 |

---

## 2. Evo 核心架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Nexus Evo 服务端架构                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              A2A Hub - 技能分享中心                        │  │
│  │  (Gene/Capsule 上传下载、任务分发、质量评估)                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ▲                                    │
│                            │ 共享技能                            │
│  ┌─────────────────────────┼─────────────────────────────────┐  │
│  │              Evo Server - 进化引擎                         │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │
│  │  │ skillDistiller│  │   solidify   │  │   mutation   │    │  │
│  │  │  (技能提炼)   │  │  (能力固化)   │  │  (经验变异)   │    │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │
│  │  │   analyzer   │  │    signals   │  │   hubReview  │    │  │
│  │  │  (信号分析)   │  │  (信号提取)  │  │ (上报审核)    │    │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ▲                                    │
│                            │ 进化指令                           │
│  ┌─────────────────────────┼─────────────────────────────────┐  │
│  │              Agent 客户端 - 执行层                          │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │
│  │  │    Grasp     │  │    Reach     │  │     Reins    │    │  │
│  │  │  (认知模块)  │  │  (执行模块)  │  │  (控制模块)  │    │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**架构说明**:

- **A2A Hub（技能分享中心）**:负责 Gene 和 Capsule 的上传下载、任务分发、质量评估
- **Evo Server（进化引擎）**:包含技能提炼、能力固化、经验变异、信号分析、信号提取、上报审核等核心模块
- **Agent 客户端（执行层）**:包括 Grasp（认知模块）、Reach（执行模块）、Reins（控制模块），负责执行任务、收集反馈、上传经验

**关键交互**:
- Agent → Evo Server:上报执行日志、请求技能提炼
- Evo Server → Agent:下发新技能、变异策略
- Agent ↔ A2A Hub:上传/下载技能、提交质量评估
- Evo Server ↔ A2A Hub:审核技能、同步元数据

### 2.2 服务端 - 客户端关系

| 层级 | 职责 | 技术实现 |
|------|------|---------|
| **Evo Server** | 进化引擎、技能提炼、共享分发 | Node.js + 信号分析 + 基因管理 |
| **A2A Hub** | 技能分享中心、质量评估、任务分发 | REST API + 认证 + 元数据管理 |
| **Agent Client** | 执行任务、收集反馈、上传经验 | GEP 协议 + 日志聚合 + 技能加载 |

---

## 3. Nexus Evo 核心功能模块

Nexus Evo 以 `@evomap/evolver` npm 包为架构蓝本，实现以下核心模块：

### 3.1 skillDistiller（技能提炼器）

**职责**:从历史执行经验中自动提取可复用的技能（Gene）。

**输入**:
- 成功执行记录（Capsules）
- 执行日志（Events）
- 现有技能库（Genes）

**处理流程**:

1. **收集蒸馏数据**:收集成功案例（成功率大于等于 70%），按 Gene 分组，计算成功率、触发信号频率
2. **分析模式**:识别高频触发模式，检测策略漂移，发现信号覆盖缺口
3. **准备蒸馏**:构建 LLM 提示词（包含成功案例、分析结果），写入提示词文件，生成蒸馏请求
4. **完成蒸馏**:解析 LLM 响应（提取 Gene JSON），验证 Gene 结构，进行去重检查，写入技能文件

**输出**:
- 新技能 Gene（带 gene_distilled_ 前缀）
- 提炼日志

**配置参数**:
- **最少成功案例数**:10
- **提炼间隔**:24 小时
- **最低成功率**:70%
- **技能最大文件数**:12

### 3.2 solidify（能力固化器）

**职责**:将一次成功的执行变更正式固化到代码库中，记录为 EvolutionEvent 和 Capsule。

**核心流程**:

1. **读取状态**:读取上次执行的 Gene ID、信号、突变信息，基线未追踪文件列表
2. **计算变更范围**:统计变更文件数、行数，分类严重程度，识别主要变更目录
3. **约束检查**:检查文件数量限制、禁止修改路径、破坏性变更检测、伦理委员会检查
4. **验证执行**:运行验证命令、Canary 检查、LLM 审核（可选）
5. **固化记录**:写入验证报告、记录进化事件、记录成功 Capsule、应用表观遗传标记
6. **自动发布（可选）**:达标 Capsule 自动发布到 A2A Hub，失败案例发布为反模式，完成 Hub 任务
7. **失败回滚**:自动恢复工作目录

**安全机制**:
- **硬封顶**:文件数量不超过 60，行数不超过 20000（不可绕过）
- **关键路径保护**:核心技能禁止修改
- **伦理审查**:检测并拒绝违规策略
- **Canary 检查**:验证索引文件可加载
- **回滚能力**:失败时自动恢复

**表观遗传机制**:
- 环境指纹（平台、架构、Node 版本）
- 成功加分、失败减分
- 标记衰减：保留最近 90 天，最多 10 个

### 3.3 mutation（变异引擎）

**职责**:根据信号上下文生成变异计划（Mutation）。

**变异类型**:
- **修复（repair）**:修复错误（log_error、errsig 触发）
- **优化（optimize）**:优化性能（无错误但机会信号）
- **创新（innovate）**:探索新策略（user_feature_request 等）

**风险等级**:
- **低（low）**:repair、optimize 默认
- **中（medium）**:innovate 默认
- **高（high）**:高风险变异（需人格约束）

**决策逻辑**:
1. 检测错误信号 → 修复
2. 检测机会信号 + 无错误 → 创新
3. 检测机会信号 + 高风险人格 → 降级为优化
4. 检测 3+ 连续修复 → 强制创新（避免修复循环）
5. 检测 5+ 连续空循环 → 强制稳态（进化饱和降级）

**输出**:变异计划 JSON，包含类型、ID、类别、触发信号、目标、预期效果、风险等级。

### 3.4 analyzer（分析器）

**职责**:分析历史执行数据，识别模式和趋势。

**分析维度**:
- 成功模式识别（高频成功参数组合）
- 失败模式识别（错误类型分布、根因分析）
- 信号频率统计（去重、抑制过度处理的信号）
- 连续失败检测（连续失败次数、失败率）
- 空循环检测（无效循环）
- 基因使用频率统计

**输出**:
- 分析报表（用于 LLM 提示词）
- 抑制信号列表（避免重复处理）
- 强制创新信号（连续失败/空循环时）

### 3.5 signals（信号提取器）

**职责**:从日志、对话、用户反馈中提取进化信号（Signals）。

**信号类型**:

**防御性信号（错误、缺失资源）**:
- 日志错误
- 错误签名
- 重复错误（3 次及以上）
- 记忆文件缺失
- 集成密钥缺失

**机会信号（创新/功能请求）**:
- 功能需求
- 改进建议
- 性能瓶颈
- 能力缺口
- 成功平台期

**特殊信号（系统级）**:
- 进化停滞
- 强制创新（修复循环后）
- 空循环检测
- 强制稳态

**提取逻辑**:
- 多语言支持（EN/ZH-CN/ZH-TW/JA）
- 上下文片段提取（用于 LLM 提示词）
- 去重抑制（避免过度处理同一信号）
- 优先级调整（成功信号优先于 cosmetic 信号）

### 3.6 hubReview（上报审核）

**职责**:对复用的 Hub 技能提交使用后质量评估。

**触发时机**:
- 来源类型为复用或参考
- solidify 完成后异步提交

**评分规则**:
- 成功且评分大于等于 0.85 → 5 分
- 成功但评分小于 0.85 → 4 分
- 失败且约束违规 → 1 分
- 失败且无约束违规 → 2 分

**防重复机制**:
- 本地文件记录已审核的资产 ID
- 最多保留 500 条记录（LRU 淘汰）

**输出**:提交到 Hub 审核接口，非阻塞，失败不影响 solidify。

---

## 4. 数据模型

### 4.1 GEP 协议概述

**GEP (Genome Evolution Protocol)** 是 Nexus Evo 的核心标准化协议，定义了基因、记忆体和进化事件的统一格式。

**GEP 三大核心组件**:

| 组件 | 英文 | 说明 | 作用 |
|------|------|------|------|
| **Gene** | 基因 | 可复用技能/策略的标准化描述 | 定义 Agent 的行为模式 |
| **Capsule** | 记忆体 | 一次完整执行过程的记录 | 记录成功经验/失败教训 |
| **Event** | 进化事件 | 进化过程的元数据记录 | 追踪进化链路和上下文 |

**GEP 设计原则**:

1. **标准化**：统一的 JSON Schema，确保跨 Agent 兼容性
2. **可追溯**：完整的血缘关系，支持进化链路追踪
3. **可共享**：通过 A2A Hub 实现技能分享
4. **可扩展**：支持自定义字段和扩展协议

### 4.1.1 Gene 标准化

**Gene 核心字段**:

```json
{
  "type": "gene",
  "schema_version": "1.0",
  "id": "gene-retry-001",
  "category": "optimize",
  "signals_match": ["timeout", "connection_error"],
  "preconditions": ["task_failed", "retry_allowed"],
  "strategy": [
    {"action": "set_timeout", "value": 30},
    {"action": "enable_exponential_backoff", "value": true},
    {"action": "log_error_signature", "value": true}
  ],
  "constraints": {
    "max_files": 10,
    "max_lines": 5000,
    "forbidden_paths": ["src/core/"]
  },
  "validation": ["npm test", "npm lint"],
  "epigenetic_marks": [
    {"mark": "platform", "value": "windows"},
    {"mark": "score", "value": 0.85}
  ],
  "asset_id": "hub-asset-001"
}
```

**字段说明**:
- `type`: 类型标识，固定为 "gene"
- `schema_version`: Schema 版本，用于向后兼容
- `id`: 基因唯一标识符
- `category`: 类别（repair/optimization/innovation）
- `signals_match`: 匹配的触发信号列表
- `preconditions`: 执行前置条件
- `strategy`: 策略步骤数组
- `constraints`: 约束条件（文件数限制、禁止路径等）
- `validation`: 验证命令列表
- `epigenetic_marks`: 表观遗传标记
- `asset_id`: A2A Hub 资产 ID（如果已共享）

### 4.1.2 Capsule 标准化

**Capsule 核心字段**:

```json
{
  "type": "capsule",
  "schema_version": "1.0",
  "id": "capsule-20260402-001",
  "trigger": ["timeout", "connection_error"],
  "gene": "gene-retry-001",
  "summary": "成功实施指数退避重试策略",
  "confidence": 0.92,
  "blast_radius": {
    "files_changed": 3,
    "lines_changed": 45
  },
  "outcome": {
    "status": "success",
    "score": 0.88
  },
  "success_streak": 5,
  "content": "完整执行过程摘要...",
  "diff": "...",
  "strategy": [...],
  "a2a": {
    "source": "local",
    "ready_for_hub": true,
    "quality_score": 0.88
  }
}
```

**字段说明**:
- `type`: 类型标识，固定为 "capsule"
- `schema_version`: Schema 版本
- `id`: 记忆体唯一标识符
- `trigger`: 触发信号列表
- `gene`: 使用的基因 ID
- `summary`: 执行摘要
- `confidence`: 置信度（0-1）
- `blast_radius`: 变更范围（文件数、行数）
- `outcome`: 结果（状态、评分）
- `success_streak`: 成功连续次数
- `content`: 完整执行过程摘要
- `diff`: 变更 diff 快照
- `strategy`: 策略步骤
- `a2a`: A2A Hub 共享属性

### 4.1.3 EvolutionEvent 标准化

**EvolutionEvent 核心字段**:

```json
{
  "type": "evolution_event",
  "schema_version": "1.0",
  "id": "event-20260402-001",
  "parent": "event-20260401-099",
  "intent": "optimize",
  "signals": ["timeout", "connection_error"],
  "genes_used": ["gene-retry-001"],
  "mutation_id": "mut-20260402-001",
  "blast_radius": {
    "files_changed": 3,
    "lines_changed": 45
  },
  "outcome": {
    "status": "success",
    "score": 0.88
  },
  "capsule_id": "capsule-20260402-001",
  "validation_report_id": "vr-20260402-001",
  "env_fingerprint": {
    "platform": "windows",
    "architecture": "x64",
    "node_version": "v22.16.0"
  },
  "meta": {
    "gene_info": {...},
    "constraint_check": {...},
    "canary_check": {...}
  }
}
```

**字段说明**:
- `type`: 类型标识，固定为 "evolution_event"
- `schema_version`: Schema 版本
- `id`: 事件唯一标识符
- `parent`: 父事件 ID（支持进化链追踪）
- `intent`: 意图（repair/optimization/innovation）
- `signals`: 触发信号
- `genes_used`: 使用的基因列表
- `mutation_id`: 变异 ID
- `blast_radius`: 变更范围
- `outcome`: 结果
- `capsule_id`: 关联的 Capsule ID
- `validation_report_id`: 验证报告 ID
- `env_fingerprint`: 环境指纹
- `meta`: 元数据

### 4.2 Gene（基因详细定义）

**基因结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 类型标识 |
| schema_version | string | 模式版本 |
| id | string | 基因 ID |
| category | string | 类别（修复/优化/创新） |
| signals_match | array | 匹配的触发信号 |
| preconditions | array | 前置条件 |
| strategy | array | 策略步骤 |
| constraints | object | 约束条件（最大文件数、禁止路径） |
| validation | array | 验证命令 |
| epigenetic_marks | array | 表观遗传标记 |
| asset_id | string | Hub 资产 ID |

**策略说明**:包含具体的策略步骤，如"增加超时时间为 30 秒"、"启用指数退避重试"、"记录错误签名用于后续分析"。

**约束条件**:限制最大文件数、禁止修改的路径等。

**表观遗传标记**:记录环境指纹、评分变化、原因说明。

### 4.3 Capsule（记忆体详细定义）

**记忆体结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 类型标识 |
| schema_version | string | 模式版本 |
| id | string | 记忆体 ID |
| trigger | array | 触发信号 |
| gene | string | 使用的基因 ID |
| summary | string | 摘要 |
| confidence | number | 置信度 |
| blast_radius | object | 变更范围（文件数、行数） |
| outcome | object | 结果（状态、评分） |
| success_streak | number | 成功连续次数 |
| content | string | 完整执行过程摘要 |
| diff | string | 变更 diff 快照 |
| strategy | array | 策略步骤 |
| a2a | object | Hub 共享属性 |

**变更范围**:包含文件数和行数的统计。

**结果**:包含状态（成功/失败）和评分。

### 4.4 EvolutionEvent（进化事件详细定义）

**进化事件结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 类型标识 |
| schema_version | string | 模式版本 |
| id | string | 事件 ID |
| parent | string | 父事件 ID |
| intent | string | 意图（修复/优化/创新） |
| signals | array | 触发信号 |
| genes_used | array | 使用的基因列表 |
| mutation_id | string | 变异 ID |
| blast_radius | object | 变更范围 |
| outcome | object | 结果 |
| capsule_id | string | 关联的 Capsule ID |
| validation_report_id | string | 验证报告 ID |
| env_fingerprint | object | 环境指纹 |
| meta | object | 元数据 |

**环境指纹**:包含平台、架构、Node 版本等信息。

**元数据**:包含基因信息、约束检查结果、Canary 检查结果。

---

## 5. Python 实现架构（Sprint 104 统一后）

### 5.1 概念模型统一

**历史背景**: 在 Sprint 104 之前，Python 实现使用了自有的 `ExtractedRule` / `SolidifiedPattern` 数据类，与设计文档中定义的 GEP 协议（Gene/Capsule/Event）不一致。这导致代码和文档"两张皮"——文档写的是 Gene/Capsule/Event，代码输出的是 Rule/Pattern。

**Sprint 104 统一后**: Python 实现完全对齐 GEP 协议，概念映射如下：

| 设计文档 (GEP 协议) | Sprint 104 前 (Python 旧模型) | 统一后 (Python 新模型) |
|---------------------|-------------------------------|------------------------|
| **Gene（基因）** | ExtractedRule | Gene dataclass |
| **Capsule（记忆体）** | SolidifiedPattern | Capsule dataclass |
| **EvolutionEvent（进化事件）** | WeightUpdate | EvolutionEvent dataclass |
| **epigenetic_marks** | weight_adjustments | epigenetic_marks |
| **Gene.category** | RuleType (CAPABILITY/PATTERN/...) | Gene.category (capability/pattern/...) |

### 5.2 模块结构

```
packages/server/src/evo/
├── gep_protocol.py          ← [NEW] GEP 协议 dataclass 定义
│   ├── Gene                 ← 替代旧 ExtractedRule
│   ├── Capsule              ← 替代旧 SolidifiedPattern
│   └── EvolutionEvent       ← 替代旧 WeightUpdate
├── distillation/
│   ├── distiller.py         ← 输出 List[Gene]（原输出 List[ExtractedRule]）
│   └── solidify.py          ← 输出 List[Capsule]（原输出 List[SolidifiedPattern]）
├── weight/
│   └── weight_updater.py    ← 输出 EvolutionEvent（原输出 WeightUpdate）
├── mutation/
│   ├── analyzer.py
│   └── mutation.py
├── a2a/
│   └── a2a.py
└── __init__.py              ← 导出 Gene, Capsule, EvolutionEvent
```

### 5.3 数据库表

**新建 3 张 GEP 表**（迁移脚本 `038_gep_tables.sql`）：

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| **genes** | 存储提取的基因（可复用技能/策略） | id, category, signals_match, strategy, constraints, epigenetic_marks |
| **capsules** | 存储固化的记忆体（成功/失败经验） | id, gene_id, summary, confidence, outcome, success_streak |
| **evolution_events** | 存储进化事件（权重变更审计） | id, parent_id, intent, genes_used, capsule_id, outcome |

**旧表处理**: `extracted_rules` 和 `solidified_patterns` 从未在 DB 中创建（代码只是内存对象），无需迁移。

### 5.4 规则类型映射

旧的 `RuleType` 枚举映射为 Gene 的 `category` 字段：

| 旧 RuleType | 新 Gene.category | 存储位置 |
|-------------|-----------------|----------|
| `CAPABILITY` | `"capability"` | Gene.strategy 中的 `recommended_capabilities` |
| `PATTERN` | `"pattern"` | Gene.preconditions + Gene.strategy |
| `ANTI_PATTERN` | `"anti_pattern"` | Gene.constraints 中的禁止条件 |
| `SEQUENCE` | `"sequence"` | Gene.strategy 中的步骤序列 |
| `CONDITION` | `"condition"` | Gene.preconditions |
| `CONSTRAINT` | `"constraint"` | Gene.constraints |

### 5.5 核心流程

```
Reins 任务执行记录（tasks 表）
         ↓
GeneDistiller.distill(task_records)  ← 原 RuleDistiller
         ↓ 提取 6 类规则 → 转换为 Gene
    List[Gene]
         ↓
Solidifier.solidify(genes)
         ↓ 过滤/去重/合并 → 转换为 Capsule
    List[Capsule]
         ↓ 写入 DB (capsules 表)
    WeightUpdater.apply_patterns(capsules)
         ↓ 从 epigenetic_marks 提取权重调整
    List[EvolutionEvent]
         ↓ 写入 DB (evolution_events 表)
    应用到 TaskAssigner 匹配权重
         ↓
下次任务派发时权重已优化
```

---

## 6. 与五兄弟的协作

### 5.1 Evo ← Grasp（认知输入）

**协作流程**:

Grasp 提供知识背景和上下文 → Evo 结合知识分析执行结果 → 生成更准确的评估

**实际实现**:
- Grasp 的知识图谱用于 enrich 信号提取
- Evo 提炼的经验回写 Grasp 作为最佳实践
- 双向同步，形成认知 - 进化闭环

### 5.2 Evo ← Reins（执行反馈）

**协作流程**:

Reins 记录任务执行日志 → Evo 分析执行数据（收集 Capsule）→ Evo 生成进化信号 → 触发 skillDistiller / solidify

**关键数据流**:
- Reins 的执行结果 → Evo 的 Capsules
- Reins 的异常日志 → Evo 的 signals
- Reins 的任务分配 → Evo 的评估反馈

### 5.3 Evo ← Vigil（安全反馈）

**协作流程**:

Vigil 记录安全相关问题 → Evo 分析安全风险模式 → 提出安全改进建议 → solidify 的 ethics 检查拦截违规策略

**安全机制集成**:
- Vigil 的安全规则 → Evo 的 forbidden_paths
- Vigil 的违规检测 → Evo 的 ethics_block_patterns
- Evo 的失败案例 → Vigil 的安全审查

### 5.4 Evo → Reach（技能输出）

**协作流程**:

Evo 提炼新技能 Gene → Reach 加载并使用 → Reach 执行结果反馈给 Evo

**技能分发流程**:
- **本地提炼**:genes.json → Reach 加载
- **Hub 分享**:A2A Hub 下载 → genes.json

### 5.5 Evo → A2A Hub（共享输出）

**共享流程**:

Capsule 达标（评分大于等于 0.78、变更安全、连续次数大于等于 2）→ Evo 打包 Gene + Capsule → 提交到 Hub 接口 → Hub 审核并存储 → 其他 Agent 下载使用

---

## 7. Evo 服务端架构

### 6.1 架构组件

```
Evo Server 架构

├── REST API
├── Job Queue
├── Worker Pool
│
└── Core Processors
    ├── DistillerWorker (skillDistiller)
    ├── SolidifyWorker (solidify)
    ├── AnalyzerWorker (analyzer + signals)
    └── HubWorker (hubReview + publish)
        │
        ├── Genes DB (genes.json)
        ├── Capsules DB (capsules)
        └── Events DB (events.jsonl)
```

**组件说明**:

- **REST API**:提供 RESTful 接口
- **Job Queue**:任务队列管理
- **Worker Pool**:工作池管理
- **Core Processors**:核心处理器，包括技能提炼、固化、分析、Hub 审核等
- **数据层**:基因数据库、记忆体数据库、事件数据库

### 6.2 API 接口

#### 6.2.1 技能管理

- **列出技能**:支持按类别、状态筛选
- **获取技能详情**:获取指定基因的详细信息
- **创建新技能**:人工审核创建
- **更新技能状态**:更新基因状态（如弃用）

#### 6.2.2 经验分析

- **获取分析报告**:返回高频模式、失败模式、覆盖缺口、信号频率
- **触发技能提炼**:手动触发蒸馏任务
- **获取提炼进度**:查询蒸馏任务状态

#### 6.2.3 能力评估

- **获取 Agent 能力评分**:查询指定 Agent 的技能评分
- **批量评估**:批量评估多个 Agent
- **获取评估报告**:获取详细的评估报告

#### 6.2.4 Hub 集成

- **列出可下载技能**:筛选高评分技能
- **获取技能详情（含 Hub 元数据）**:获取 Hub 上的技能信息
- **提交使用反馈**:提交使用体验评价

### 6.3 后台任务调度

**任务配置**:

- **技能提炼**:每小时执行，最少 10 个成功案例
- **分析**:每 6 小时执行，分析最近 30 天数据
- **清理**:每周日执行，保留 90 天数据

---

## 8. 性能指标

### 7.1 处理能力

| 指标 | P50 | P95 | P99 |
|------|-----|-----|-----|
| 技能提炼时间 | 30 秒 | 2 分钟 | 5 分钟 |
| solidify 执行 | 10 秒 | 30 秒 | 60 秒 |
| 信号分析 | 1 秒 | 5 秒 | 10 秒 |
| Hub 审核 | 5 秒 | 15 秒 | 30 秒 |

### 7.2 吞吐量

| 指标 | 目标值 |
|------|-------|
| 每日技能提炼 | 10+ |
| 每日技能发布 | 5+ |
| 每日 Hub 审核 | 20+ |
| 并发任务数 | 5+ |

---

## 9. 监控与告警

### 8.1 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 技能失败率 | 技能执行失败比例 | 大于 15% |
| 提炼成功率 | 技能提炼任务成功率 | 小于 80% |
| Hub 审核通过率 | 发布技能通过率 | 小于 70% |
| 连续空循环 | 无效进化次数 | 大于等于 5 次 |
| 进化饱和 | 连续 0 变更 | 大于等于 3 次 → 降级稳态 |

### 8.2 安全监控

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 硬封顶触发 | 文件/行数超限 | 1 次 → 紧急告警 |
| 关键路径修改 | 修改核心技能 | 1 次 → 阻断 + 告警 |
| 伦理审查失败 | 检测到违规策略 | 1 次 → 阻断 + 告警 |
| Canary 失败 | 索引文件无法加载 | 1 次 → 回滚 + 告警 |

---

## 10. 版本控制

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-04-02 | 初始版本 | 麻子 |
| v1.2 | 2026-04-02 | 接口对标 MLflow + 补充使用场景 | 麻子 |
| v1.3 | 2026-04-02 | **重构为 evolver 参考，补充服务端架构** | **麻子** |
| v1.4 | 2026-04-03 | **移除 MLflow 引用，完善 GEP 协议文档，明确 Evo 服务端职责划分** | **麻子** |
| v1.5 | 2026-06-01 | **Sprint 104: Python 实现统一为 GEP 协议（Rule/Pattern → Gene/Capsule/Event），新建 3 张 GEP 表** | **刚子** |

---

## 11. 参考文档

1. [@evomap/evolver](E:\openclaw-workspace\.openclaw\workspace\node_modules\@evomap\evolver\src\gep) - 核心参考实现
2. [00-platform-architecture.md](./00-platform-architecture.md) - 平台架构
3. [02-reins-architecture.md](./02-reins-architecture.md) - 御（工作流）
4. [01-grasp-architecture.md](./01-grasp-architecture.md) - 悟（认知）
5. [GEP Protocol](https://github.com/evomap/evolver) - GEP 协议规范
6. [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/) - ML 工作流（参考）
7. [OpenAPI 3.0](https://spec.openapis.org/oas/v3.0.3) - RESTful 接口规范

---

**文档状态**: ✅ 已完成 v1.5 修正
- Human on the Loop 原则已明确（02-reins）
- MLflow 引用已移除，改为 evolver 参考（03-evo）
- GEP 协议标准化已补充（Gene/Capsule/Event）
- Evo 服务端架构职责已完善
- **Sprint 104**: Python 实现统一为 GEP 协议，新建 5.1-5.5 节记录概念模型统一、模块结构、DB 表、规则映射、核心流程
