---
name: grasp
description: 知识图谱注册、检索和注入。提供领域知识查询、认知模式管理和最佳实践检索，是智能体的认知底座。
tags: [cognitive, knowledge, memory, retrieval, nexus]
---

# Grasp Skill

**版本**: v1.0  
**作者**: 谷子  
**日期**: 2026-04-03  
**状态**: 开发中

---

## 1. 概述

Grasp Skill 是 Nexus 认知系统的对外接口封装，提供认知任务的注册、注入、检索、更新四个核心能力。

### 1.1 技能定位

- **所属层**: Nexus Grasp（悟）- 认知层
- **作用**: 封装认知系统能力，供 智能体 内部调用
- **对齐标准**: MCP Protocol（工具、资源、提示词）

### 1.2 核心能力

| 能力 | 接口 | 说明 |
|------|------|------|
| **注册** | `register()` | 注册认知模式、标签体系、审核规则 |
| **注入** | `inject()` | 将新认知注入到本地知识库 |
| **检索** | `retrieve()` | 从知识库检索匹配的认知条目 |
| **更新** | `update()` | 更新已存在的认知条目 |

---

## 2. 接口定义

### 2.1 register - 认知注册

注册认知模式的定义、标签体系、审核规则等基础配置。

**方法签名**:

```typescript
interface RegisterOptions {
  // 认知类型定义
  cognitionTypes?: CognitionType[];
  
  // 标签体系
  tagSystem?: TagSystem;
  
  // 审核规则
  reviewRules?: ReviewRule[];
  
  // 质量评估规则
  qualityRules?: QualityRule[];
}

interface CognitionType {
  id: string;              // 类型 ID
  name: string;            // 类型名称
  description: string;     // 类型描述
  schema: object;          // JSON Schema 定义
}

interface TagSystem {
  rootTags: string[];      // 根标签
  tagRules: TagRule[];     // 标签规则
}

interface TagRule {
  parent: string;          // 父标签
  children: string[];      // 子标签
  allowed: boolean;        // 是否允许使用
}

interface ReviewRule {
  id: string;              // 规则 ID
  condition: string;       // 触发条件（表达式）
  action: 'auto_approve' | 'auto_reject' | 'manual_review';
  confidenceThreshold?: number;
}

interface QualityRule {
  id: string;              // 规则 ID
  dimension: string;       // 评估维度
  weight: number;          // 权重
  calculation: string;     // 计算逻辑
}
```

**返回结果**:

```typescript
interface RegisterResult {
  status: 'success' | 'partial' | 'failed';
  registered: number;      // 成功注册数量
  errors: ErrorInfo[];     // 错误信息
}
```

**使用场景**:
- 初始化认知模式定义
- 更新标签体系
- 配置审核规则
- 调整质量评估标准

---

### 2.2 inject - 认知注入

将新的认知/知识注入到本地知识库。

**方法签名**:

```typescript
interface InjectOptions {
  // 认知类型
  type: 'fact' | 'pattern' | 'lesson' | 'meta';
  
  // 认知内容
  content: string;
  
  // 来源信息
  source: {
    智能体_id: string;      // 来源 智能体 ID
    task_id?: string;      // 关联任务 ID
    channel: string;       // 来源渠道
  };
  
  // 可选参数
  tags?: string[];         // 标签列表
  confidence?: number;     // 置信度 0-1，默认 0.8
  metadata?: object;       // 附加元数据
  domain?: string;         // 领域标签，如 "金融"、"项目管理"
}

interface InjectResult {
  cognition_id: string;    // 注入成功后生成的认知 ID
  status: 'injected' | 'pending_review' | 'rejected';
  quality_score: number;   // 质量评分 0-1
  created_at: string;      // 创建时间
}
```

**内部流程**:

1. **格式验证** - 检查 content 格式、长度、编码
2. **安全检测** - 调用 PoisonDetector 检测投毒风险
3. **质量评分** - 调用 QualityValidator 计算初始评分
4. **状态判断** - 根据评分确定状态（已发布/待审核/已拒绝）
5. **写入存储** - 写入对应的存储位置
6. **返回结果** - 返回认知 ID 和状态

**错误码**:

| 错误码 | 说明 | 重试策略 |
|--------|------|---------|
| INVALID_CONTENT | 内容格式无效 | 不重试 |
| POISON_DETECTED | 检测到投毒风险 | 不重试 |
| LOW_QUALITY | 质量评分低于阈值 | 不重试 |
| STORAGE_ERROR | 存储写入失败 | 指数退避 3 次 |

---

### 2.3 retrieve - 认知检索

从知识库检索匹配的认知条目。

**方法签名**:

```typescript
interface RetrieveQuery {
  // 查询文本（必填）
  query: string;
  
  // 过滤条件
  type?: ('fact' | 'pattern' | 'lesson' | 'meta')[];
  tags?: string[];         // 限定标签（AND 匹配）
  min_confidence?: number; // 最低置信度阈值
  min_quality?: number;    // 最低质量评分
  source_智能体?: string;   // 来源 智能体 ID
  domain?: string;          // 领域过滤
  
  // 分页参数
  limit?: number;          // 返回数量上限，默认 10
  offset?: number;         // 分页偏移，默认 0
}

interface RetrieveResult {
  items: CognitionItem[];  // 匹配的认知条目列表
  total: number;           // 匹配总数
  has_more: boolean;       // 是否有更多结果
  query_time_ms: number;   // 查询耗时（毫秒）
}

interface CognitionItem {
  cognition_id: string;    // 认知 ID
  type: string;            // 认知类型
  content: string;         // 认知内容
  tags: string[];          // 标签列表
  confidence: number;      // 置信度
  quality_score: number;   // 质量评分
  source: {
    智能体_id: string;
    task_id?: string;
    channel: string;
  };
  created_at: string;      // 创建时间
  updated_at: string;      // 更新时间
  status: 'published' | 'pending_review' | 'rejected';
  domain?: string;          // 领域标签
}
```

**内部流程**:

1. **意图解析** - 解析 query，提取关键实体和意图
2. **向量检索** - 在向量库中检索语义相似条目
3. **关键词检索** - 执行关键词匹配
4. **结果融合** - 合并向量和关键词结果
5. **过滤排序** - 按 type、tags、min_confidence 过滤，按相关度排序
6. **分页返回** - 按 limit/offset 分页返回

---

### 2.4 update - 认知更新

更新已存在的认知条目。

**方法签名**:

```typescript
interface CognitionUpdate {
  content?: string;        // 新内容
  tags?: string[];         // 新标签列表
  confidence?: number;     // 新置信度
  metadata?: object;       // 新元数据
}

interface UpdateResult {
  cognition_id: string;    // 更新的认知 ID
  status: 'updated' | 'pending_review' | 'rejected';
  quality_score: number;   // 更新后质量评分
  updated_at: string;      // 更新时间
  version: number;         // 新版本号
}
```

**内部流程**:

1. **存在性检查** - 确认 cognition_id 存在
2. **权限检查** - 检查更新权限（来源 智能体 或审核通过）
3. **变更检测** - 对比新旧内容，判断变更类型
4. **重新评分** - 内容变更时重新调用安全检测和质量评分
5. **原子更新** - 原子性更新存储中的记录
6. **版本记录** - 记录变更历史

**错误码**:

| 错误码 | 说明 | 重试策略 |
|--------|------|---------|
| NOT_FOUND | 认知 ID 不存在 | 不重试 |
| FORBIDDEN | 无更新权限 | 不重试 |
| INVALID_UPDATE | 更新内容无效 | 不重试 |

---

## 3. 数据模型

### 3.1 认知类型

| 类型 | 英文 | 说明 | 示例 |
|------|------|------|------|
| 事实 | fact | 客观事实、定义、知识 | "Docker 镜像拉取命令是 docker pull" |
| 模式 | pattern | 行为模式、思维模式、解决方案模式 | "任务分解时，应先识别依赖关系再安排并行" |
| 经验 | lesson | 从任务执行中总结的经验教训 | "vLLM 部署时 GPU 显存不足，需调整 max_model_len" |
| 元认知 | meta | 关于认知本身的认知（学习如何学习） | "认知注入应遵循来源可追溯原则" |

### 3.2 认知状态

| 状态 | 说明 | 可检索 | 自动流转 |
|------|------|--------|---------|
| published | 已发布 | 是 | - |
| pending_review | 待审核 | 否 | 审核通过后→published/rejected |
| rejected | 已拒绝 | 否 | 30 天后自动归档 |

### 3.3 本地存储结构

```
memory/grasp/
├── schema.yaml              # 认知 schema 定义
├── tag_system.yaml          # 标签体系定义
├── review_rules.yaml        # 审核规则定义
├── cognitions.jsonl         # 认知条目（追加模式）
└── index/
    ├── vector.index         # 向量索引
    └── keyword.index        # 关键词索引
```

**cognitions.jsonl 格式**:

```json
{
  "cognition_id": "cog-20260403-001",
  "type": "lesson",
  "content": "任务分解时，应先识别依赖关系再安排并行",
  "tags": ["任务分解", "最佳实践"],
  "confidence": 0.9,
  "quality_score": 0.85,
  "source": {
    "智能体_id": "智能体-001",
    "task_id": "task-123",
    "channel": "execution_feedback"
  },
  "status": "published",
  "version": 1,
  "created_at": "2026-04-03T10:00:00Z",
  "updated_at": "2026-04-03T10:00:00Z"
}
```

---

## 4. MCP 协议对齐

### 4.1 工具定义

Grasp Skill 的四个接口作为 MCP Tool 对外提供：

```json
{
  "tools": [
    {
      "name": "grasp_register",
      "description": "注册认知模式的定义、标签体系、审核规则",
      "inputSchema": {
        "type": "object",
        "properties": {
          "cognitionTypes": {
            "type": "array",
            "items": { "$ref": "#/components/schemas/CognitionType" }
          },
          "tagSystem": { "$ref": "#/components/schemas/TagSystem" },
          "reviewRules": {
            "type": "array",
            "items": { "$ref": "#/components/schemas/ReviewRule" }
          }
        }
      }
    },
    {
      "name": "grasp_inject",
      "description": "将新认知注入到知识库",
      "inputSchema": {
        "type": "object",
        "properties": {
          "type": { "enum": ["fact", "pattern", "lesson", "meta"] },
          "content": { "type": "string" },
          "source": { "$ref": "#/components/schemas/SourceInfo" },
          "tags": {
            "type": "array",
            "items": { "type": "string" }
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        },
        "required": ["type", "content", "source"]
      }
    },
    {
      "name": "grasp_retrieve",
      "description": "从知识库检索认知",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "type": {
            "type": "array",
            "items": { "enum": ["fact", "pattern", "lesson", "meta"] }
          },
          "tags": {
            "type": "array",
            "items": { "type": "string" }
          },
          "min_confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "limit": { "type": "number", "default": 10 }
        },
        "required": ["query"]
      }
    },
    {
      "name": "grasp_update",
      "description": "更新已有认知",
      "inputSchema": {
        "type": "object",
        "properties": {
          "cognition_id": { "type": "string" },
          "content": { "type": "string" },
          "tags": {
            "type": "array",
            "items": { "type": "string" }
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        },
        "required": ["cognition_id"]
      }
    }
  ]
}
```

### 4.2 资源定义

认知条目作为 MCP Resource 对外暴露：

```json
{
  "resources": [
    {
      "uri": "grasp://cognition/{id}",
      "name": "认知条目",
      "mimeType": "application/json"
    },
    {
      "uri": "grasp://cognitions",
      "name": "认知列表",
      "mimeType": "application/json"
    },
    {
      "uri": "grasp://types",
      "name": "认知类型定义",
      "mimeType": "application/json"
    },
    {
      "uri": "grasp://tags",
      "name": "标签体系",
      "mimeType": "application/json"
    }
  ]
}
```

---

## 5. 实现规范

### 5.1 文件结构

```
skills/grasp/
├── Skill.md                          # 本文件
├── README.md                         # 使用指南
├── implementation/
│   ├── index.ts                      # 入口文件
│   ├── types.ts                      # TypeScript 类型定义
│   ├── register.ts                   # register 实现
│   ├── inject.ts                     # inject 实现
│   ├── retrieve.ts                   # retrieve 实现
│   ├── update.ts                     # update 实现
│   └── storage/
│       ├── indexer.ts                # 索引器
│       ├── store.ts                  # 存储层
│       └── migration.ts              # 迁移脚本
├── tests/
│   ├── register.test.ts
│   ├── inject.test.ts
│   ├── retrieve.test.ts
│   └── update.test.ts
└── seed/
    ├── schema.yaml                   # 初始 schema
    ├── seed_cognitions.jsonl         # 种子认知数据
    └── tag_system.yaml               # 初始标签体系
```

### 5.2 依赖项

```json
{
  "dependencies": {
    "vectordb": ">=1.0.0",          // 向量数据库（如 Milvus/Faiss）
    "jsonl-store": ">=1.0.0",       // JSONL 存储库
    "schema-validator": ">=1.0.0",  // Schema 验证库
    "poison-detector": ">=1.0.0",   // 投毒检测器
    "quality-validator": ">=1.0.0"  // 质量验证器
  },
  "devDependencies": {
    "@types/node": ">=18.0.0",
    "typescript": ">=5.0.0",
    "jest": ">=29.0.0"
  }
}
```

### 5.3 错误处理规范

所有错误应遵循以下格式：

```typescript
interface GraspError {
  code: string;              // 错误码
  message: string;           // 错误消息
  details?: object;          // 详细错误信息
  retryable: boolean;        // 是否可重试
}
```

### 5.4 日志规范

所有操作应记录日志，包含：

```typescript
interface GraspLog {
  timestamp: string;
  action: string;            // 操作名称
  cognition_id?: string;     // 认知 ID
  智能体_id: string;          // 智能体 ID
  status: 'success' | 'failure';
  error?: GraspError;
  duration_ms?: number;      // 操作耗时
}
```

---

## 6. 使用示例

### 6.1 注册认知模式

```typescript
// 注册认知类型和标签体系
await 智能体.grasp.register({
  cognitionTypes: [
    {
      id: "task_decomposition",
      name: "任务分解",
      description: "任务分解相关的认知类型",
      schema: {
        type: "object",
        properties: {
          task: { type: "string" },
          subtasks: { type: "array", items: { type: "string" } },
          dependencies: { type: "object" }
        }
      }
    }
  ],
  tagSystem: {
    rootTags: ["任务分解", "最佳实践", "错误模式", "工具使用"],
    tagRules: [
      { parent: "任务分解", children: ["依赖分析", "并行调度"], allowed: true }
    ]
  },
  reviewRules: [
    {
      id: "high_confidence_auto_approve",
      condition: "confidence > 0.95",
      action: "auto_approve",
      confidenceThreshold: 0.95
    }
  ]
});
```

### 6.2 注入认知

```typescript
// 注入一条任务分解经验
const result = await 智能体.grasp.inject({
  type: "lesson",
  content: "任务分解时，应先识别依赖关系再安排并行",
  source: {
    智能体_id: "智能体-001",
    task_id: "task-123",
    channel: "execution_feedback"
  },
  tags: ["任务分解", "最佳实践"],
  confidence: 0.9
});

console.log(`认知注入成功：${result.cognition_id}`);
```

### 6.3 检索认知

```typescript
// 检索任务分解相关认知
const result = await 智能体.grasp.retrieve({
  query: "任务分解的最佳实践",
  type: ["lesson", "pattern"],
  tags: ["最佳实践"],
  min_confidence: 0.7,
  limit: 5
});

console.log(`找到 ${result.total} 条认知`);
for (const item of result.items) {
  console.log(`${item.cognition_id}: ${item.content}`);
}
```

### 6.4 更新认知

```typescript
// 更新认知
const result = await 智能体.grasp.update("cog-20260403-001", {
  content: "任务分解时，应先识别任务依赖关系，再安排并行执行",
  confidence: 0.95
});

console.log(`认知更新成功，新版本：${result.version}`);
```

---

## 7. 性能指标

### 7.1 响应时间

| 操作 | P50 | P95 | P99 |
|------|-----|-----|-----|
| register | 50ms | 150ms | 300ms |
| inject | 100ms | 300ms | 500ms |
| retrieve | 50ms | 150ms | 300ms |
| update | 80ms | 200ms | 400ms |

### 7.2 吞吐量

| 指标 | 目标值 |
|------|-------|
| 并发 register | 100 QPS |
| 并发 inject | 200 QPS |
| 并发 retrieve | 1000 QPS |
| 并发 update | 200 QPS |

---

## 8. 监控与告警

### 8.1 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| inject 失败率 | 注入操作失败比例 | >5% |
| retrieve 延迟 | 检索操作耗时 P95 | >500ms |
| 待审核数量 | pending_review 数量 | >100 |
| 投毒拦截率 | PoisonDetector 拦截比例 | >10% |
| 质量评分分布 | 平均质量评分 | <0.5 |

### 8.2 审计日志

所有认知操作应记录审计日志，包含：

- 操作类型（inject/retrieve/update/register）
- 认知 ID
- 操作人（智能体 ID）
- 操作结果
- 操作耗时
- 错误信息（如有）

---

## 9. 版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-04-03 | 初始版本，包含 register/inject/retrieve/update 四个接口 | 谷子 |

---

## 10. 待开发清单

- [ ] 实现 `register()` 接口
- [ ] 实现 `inject()` 接口（含安全检测）
- [ ] 实现 `retrieve()` 接口（向量检索 + 关键词检索）
- [ ] 实现 `update()` 接口
- [ ] 实现本地存储层（JSONL + 索引）
- [ ] 实现投毒检测器（PoisonDetector）
- [ ] 实现质量验证器（QualityValidator）
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 准备种子数据
- [ ] MCP 协议集成验证

---

**文档状态**: ✅ 设计完成  **下一步**: 开始实现四个核心接口
