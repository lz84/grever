# Nexus Grasp Skill 接口设计

**版本**: v1.0  
**作者**: 谷子  
**日期**: 2026-04-03  
**状态**: 设计中

---

## 1. 概述

**Grasp Skill** 是 Nexus Agent SDK 中认知系统的对外接口封装，提供 inject、retrieve、update 三个核心接口。

### 1.1 设计背景

根据 Agent SDK 架构原则：
- SDK 和技能的出入口**必须是 Agent**，不接受外部直接 API 调用
- 技能是 Agent 端组件，没有网络 API，必须通过 Agent 方法调用
- Grasp Skill 封装认知系统能力，供 Agent 内部调用

### 1.2 与 MCP 协议的关系

MCP（Model Context Protocol）定义了 AI 模型与工具/数据源交互的标准方式。Grasp Skill 遵循 MCP 协议规范，提供标准的工具接口：

| MCP 概念 | Grasp Skill 实现 |
|---------|-----------------|
| Tool | inject / retrieve / update |
| Resource | 知识条目（KnowledgeItem） |
| Prompt | 认知模板（预定义查询模式） |

---

## 2. 接口设计

### 2.1 inject - 认知注入

将新的认知/知识注入到本地知识库。

**方法签名**:

```
inject(cognition: CognitionInput) -> InjectResult
```

**输入参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | enum | 是 | 认知类型：fact（事实）/ pattern（模式）/ lesson（经验）/ meta（元认知） |
| content | string | 是 | 认知内容文本 |
| source | SourceInfo | 是 | 来源信息 |
| tags | string[] | 否 | 标签列表 |
| confidence | number | 否 | 置信度 0-1，默认 0.8 |
| metadata | object | 否 | 附加元数据 |

**SourceInfo 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | string | 来源 Agent ID |
| task_id | string | 关联任务 ID |
| channel | string | 来源渠道 |

**返回结果**:

| 字段 | 类型 | 说明 |
|------|------|------|
| cognition_id | string | 注入成功后生成的认知 ID |
| status | enum | injected（已注入）/ pending_review（待审核）/ rejected（已拒绝） |
| quality_score | number | 质量评分 0-1 |

**内部流程**:

1. **格式验证** - 检查 content 格式、长度、编码
2. **安全检测** - 调用 PoisonDetector 检测投毒风险
3. **质量评分** - 调用 QualityValidator 计算初始评分
4. **写入存储** - 根据 status 写入对应存储（已发布/待审核/已拒绝）
5. **返回结果** - 返回认知 ID 和状态

**错误码**:

| 错误码 | 说明 |
|--------|------|
| INVALID_CONTENT | 内容格式无效 |
| POISON_DETECTED | 检测到投毒风险 |
| LOW_QUALITY | 质量评分低于阈值 |
| STORAGE_ERROR | 存储写入失败 |

---

### 2.2 retrieve - 认知检索

从知识库检索匹配的认知条目。

**方法签名**:

```
retrieve(query: RetrieveQuery) -> RetrieveResult
```

**输入参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 查询文本 |
| type | enum[] | 否 | 限定认知类型 |
| tags | string[] | 否 | 限定标签（AND 匹配） |
| min_confidence | number | 否 | 最低置信度阈值 |
| limit | number | 否 | 返回数量上限，默认 10 |
| offset | number | 否 | 分页偏移，默认 0 |

**返回结果**:

| 字段 | 类型 | 说明 |
|------|------|------|
| items | CognitionItem[] | 匹配的认知条目列表 |
| total | number | 匹配总数 |
| has_more | boolean | 是否有更多结果 |

**CognitionItem 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| cognition_id | string | 认知 ID |
| type | enum | 认知类型 |
| content | string | 认知内容 |
| tags | string[] | 标签列表 |
| confidence | number | 置信度 |
| quality_score | number | 质量评分 |
| source | SourceInfo | 来源信息 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

**内部流程**:

1. **意图解析** - 解析 query，提取关键实体和意图
2. **向量检索** - 在向量库中检索语义相似条目
3. **关键词检索** - 执行关键词匹配
4. **结果融合** - 合并向量和关键词结果
5. **过滤排序** - 按 type、tags、min_confidence 过滤，按相关度排序
6. **分页返回** - 按 limit/offset 分页返回

---

### 2.3 update - 认知更新

更新已存在的认知条目。

**方法签名**:

```
update(cognition_id: string, update: CognitionUpdate) -> UpdateResult
```

**输入参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| cognition_id | string | 是 | 要更新的认知 ID |
| content | string | 否 | 新内容（与 inject 相同格式） |
| tags | string[] | 否 | 新标签列表 |
| confidence | number | 否 | 新置信度 |
| metadata | object | 否 | 新元数据 |

**返回结果**:

| 字段 | 类型 | 说明 |
|------|------|------|
| cognition_id | string | 更新的认知 ID |
| status | enum | updated（已更新）/ pending_review（待审核）/ rejected（已拒绝） |
| quality_score | number | 更新后质量评分 |
| updated_at | timestamp | 更新时间 |

**内部流程**:

1. **存在性检查** - 确认 cognition_id 存在
2. **权限检查** - 检查更新权限（来源 Agent 或审核通过）
3. **变更检测** - 对比新旧内容，判断变更类型
4. **重新评分** - 内容变更时重新调用安全检测和质量评分
5. **原子更新** - 原子性更新存储中的记录
6. **版本记录** - 记录变更历史

**错误码**:

| 错误码 | 说明 |
|--------|------|
| NOT_FOUND | 认知 ID 不存在 |
| FORBIDDEN | 无更新权限 |
| INVALID_UPDATE | 更新内容无效 |

---

## 3. 数据模型

### 3.1 认知类型

| 类型 | 英文 | 说明 |
|------|------|------|
| 事实 | fact | 客观事实、定义、知识 |
| 模式 | pattern | 行为模式、思维模式、解决方案模式 |
| 经验 | lesson | 从任务执行中总结的经验教训 |
| 元认知 | meta | 关于认知本身的认知（学习如何学习） |

### 3.2 认知状态

| 状态 | 说明 | 可检索 |
|------|------|--------|
| published | 已发布 | 是 |
| pending_review | 待审核 | 否（审核通过后变为 published 或 rejected） |
| rejected | 已拒绝 | 否 |

### 3.3 存储结构

**本地存储**（遵循 ontology skill 模式）:

```
memory/grasp/
├── cognition.jsonl      # 认知条目（追加模式）
├── schema.yaml          # 认知 schema 定义
└── index/               # 向量索引
```

---

## 4. 与 MCP 协议的对应

### 4.1 工具定义

Grasp Skill 的三个接口作为 MCP Tool 对外提供：

```json
{
  "tools": [
    {
      "name": "grasp_inject",
      "description": "将新认知注入到知识库",
      "inputSchema": {
        "type": "object",
        "properties": {
          "type": { "enum": ["fact", "pattern", "lesson", "meta"] },
          "content": { "type": "string" },
          "source": { "type": "object" },
          "tags": { "type": "array", "items": { "type": "string" } },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
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
          "type": { "type": "array", "items": { "type": "string" } },
          "tags": { "type": "array", "items": { "type": "string" } },
          "min_confidence": { "type": "number", "minimum": 0, "maximum": 1 },
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
          "tags": { "type": "array", "items": { "type": "string" } },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
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
    }
  ]
}
```

---

## 5. 调用示例

### 5.1 注入认知

```javascript
// Agent 内部调用
const result = await agent.grasp.inject({
  type: "lesson",
  content: "任务分解时，应先识别依赖关系再安排并行",
  source: {
    agent_id: "agent-001",
    task_id: "task-123",
    channel: "execution_feedback"
  },
  tags: ["任务分解", "最佳实践"],
  confidence: 0.9
});
// result.cognition_id = "cog-xxx"
// result.status = "published"
```

### 5.2 检索认知

```javascript
// Agent 内部调用
const result = await agent.grasp.retrieve({
  query: "任务分解的最佳实践",
  type: ["lesson", "pattern"],
  tags: ["最佳实践"],
  min_confidence: 0.7,
  limit: 5
});
// result.items = [...]
```

### 5.3 更新认知

```javascript
// Agent 内部调用
const result = await agent.grasp.update("cog-xxx", {
  content: "修正后的内容",
  confidence: 0.95
});
// result.status = "updated"
```

---

## 6. 错误处理

### 6.1 错误响应格式

```json
{
  "error": {
    "code": "POISON_DETECTED",
    "message": "检测到认知投毒风险，内容已被拒绝",
    "details": {
      "risk_score": 0.85,
      "risk_factors": ["contradicts_existing", "unknown_source"]
    }
  }
}
```

### 6.2 重试策略

| 错误类型 | 重试策略 |
|---------|---------|
| STORAGE_ERROR | 指数退避，最多 3 次 |
| NETWORK_ERROR | 指数退避，最多 3 次 |
| 其他错误 | 不重试，直接返回 |

---

## 7. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-04-03 | 初始版本，包含 inject/retrieve/update 三个接口 |

---

## 8. 待明确事项

1. **审核流程细节** - 待审核的认知如何触发人工审核流程
2. **多 Agent 协作** - 多个 Agent 对同一认知的并发更新冲突处理
3. **同步机制** - 本地认知与 Nexus 悟的同步策略
