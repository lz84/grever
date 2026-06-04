# Nexus Reins-Grasp 调用集成设计方案

**版本**: v1.0
**日期**: 2026-04-04
**作者**: 谷子
**任务编号**: MAK-77

---

## 1. 概述

### 1.1 设计目标

设计 Reins（御）调用 Grasp（悟）的集成方案，包含三大核心策略：

| 策略 | 描述 | 优先级 |
|------|------|--------|
| **调用策略** | Reins 如何、何时调用 Grasp | P0 |
| **缓存策略** | Grasp 响应结果的缓存机制 | P0 |
| **降级策略** | Grasp 不可用时的 fallback | P0 |

### 1.2 背景

根据 nexus-vision.md 的架构设计：

```
悟（Grasp）提供认知 → 御（Reins）驾驭智能体协同工作 → 产生执行数据
                        ↓
                  双向认知流
                        ↓
悟（Grasp）← 工作中产生新认知 → 回流悟（Grasp）
```

Reins 是驾驭层，负责任务编排和智能体协同。Reins 在以下场景需要调用 Grasp：

1. **任务分解时**：理解用户高层目标，需要 Grasp 提供领域认知
2. **智能体匹配时**：了解智能体能力画像，需要 Grasp 提供知识支撑
3. **执行监控时**：需要 Grasp 提供上下文理解
4. **结果复盘时**：将执行经验反馈给 Grasp（认知回流）

### 1.3 集成范围

```
┌──────────────────────────────────────────────────────────────────┐
│                         Reins 服务端                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  任务管理器  │  智能体注册  │  工作流引擎  │  状态机       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                    ┌──────────┴──────────┐                      │
│                    │   Grasp 调用适配器   │                      │
│                    │  (本设计文档主题)    │                      │
│                    └──────────┬──────────┘                      │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Grasp 认知层        │
                    │  - 意图理解              │
                    │  - 知识检索              │
                    │  - 领域认知              │
                    └─────────────────────────┘
```

---

## 2. 调用策略

### 2.1 调用场景分类

Reins 调用 Grasp 分为两类场景：

| 场景 | 调用类型 | 描述 | 典型耗时 |
|------|---------|------|----------|
| **同步调用** | Request-Response | 需要立即获取结果 | 100-500ms |
| **异步调用** | Fire-and-Forget | 不阻塞主流程 | 无明确耗时 |

### 2.2 同步调用场景

#### 场景 1：任务分解时的意图理解

**触发时机**：用户输入高层目标，Reins 需要将其分解为可执行任务

**调用方式**：
```
Reins → Grasp: 发送用户目标文本
Grasp → Reins: 返回意图 + 领域上下文 + 推荐任务模板
```

**请求格式**：
```yaml
IntentUnderstandingRequest:
  user_goal: string          # 用户原始目标
  context:
    project_id: string       # 当前项目ID
    agent_capabilities: []   # 可用智能体能力列表
  options:
    max_tasks: int = 10     # 最大任务数
    include_templates: bool  # 是否返回推荐模板
```

**响应格式**：
```yaml
IntentUnderstandingResponse:
  intent:
    type: string            # goal_type
    confidence: float       # 置信度 0-1
    entities: []            # 识别的实体
  domain_context:
    domain: string          # 领域分类
    relevant_concepts: []   # 相关概念列表
    constraints: []         # 约束条件
  suggested_tasks:
    - task_template: string
      priority: int
      required_capabilities: []
  cache_key: string         # 用于缓存
```

**超时配置**：
- 默认超时：5 秒
- 重试次数：2 次
- 降级策略：返回默认任务模板

#### 场景 2：智能体能力匹配

**触发时机**：任务需要分配给智能体，需要匹配最合适的智能体

**调用方式**：
```
Reins → Grasp: 发送任务需求 + 智能体列表
Grasp → Reins: 返回最佳匹配排序
```

**请求格式**：
```yaml
AgentMatchingRequest:
  task_requirements:
    required_capabilities: []
    preferred_experience: []
    constraints: []
  available_agents:
    - agent_id: string
      capabilities: []
      historical_performance: {}
  context:
    task_type: string
    urgency: string
```

**响应格式**：
```yaml
AgentMatchingResponse:
  recommendations:
    - agent_id: string
      match_score: float      # 0-1
      reasoning: string
      risk_factors: []
  fallback_agents: []          # 备选智能体
  cache_key: string
```

**超时配置**：
- 默认超时：2 秒
- 重试次数：1 次
- 降级策略：使用负载均衡返回

### 2.3 异步调用场景

#### 场景 3：任务执行监控

**触发时机**：任务执行过程中，定期获取上下文更新

**调用方式**：
```
Reins → Grasp: 发送执行状态（不等待响应）
Grasp → Reins: 通过回调更新上下文
```

**请求格式**：
```yaml
ExecutionMonitoringRequest:
  task_id: string
  execution_state:
    current_step: string
    progress: float          # 0-100%
    outputs: {}
  callbacks:
    context_update: string   # 回调URL
    completion: string       # 完成回调URL
```

**特点**：
- 非阻塞调用
- Grasp 异步分析并推送更新
- 用于异常检测和上下文补全

#### 场景 4：认知回流

**触发时机**：任务完成后，将执行经验反馈给 Grasp

**调用方式**：
```
Reins → Grasp: 发送执行结果（不等待响应）
Grasp → Reins: 确认接收（异步）
```

**请求格式**：
```yaml
CognitiveFeedbackRequest:
  task_id: string
  execution_result:
    success: bool
    outputs: {}
    errors: []
    duration_ms: int
  learnings:
    what_worked: []
    what_did_not_work: []
    suggestions: []
  metadata:
    agent_id: string
    task_type: string
    timestamp: string
```

**特点**：
- Fire-and-Forget 模式
- Grasp 异步处理进入审核流程
- 不影响 Reins 主流程

#### 场景 5：任务派发时的认知抽取

**触发时机**：任务分解完成后、正式派发给 Agent 之前，Reins 需要为任务附上相关认知上下文

**调用方式**：
```
Reins → Grasp: 发送任务描述 + 任务类型
Grasp → Reins: 返回相关认知列表（设计文档、Pattern、Lesson 等）
Reins → Agent: 任务 + 认知上下文（打包下发）
```

**请求格式**：
```yaml
DispatchCognitionRequest:
  task:
    id: string
    title: string
    description: string
    type: string          # development | analysis | review | design | research
    context:
      project: string      # 项目名称
      domain: string       # 领域分类
  options:
    max_cognitions: int   # 最多返回多少条认知（默认按 task.type 自动推断，可覆盖）
    include_sources: bool = true  # 是否附带来源文档信息
```

**自动档位规则**（`options.max_cognitions` 未指定时）：

| task.type | max_cognitions |
|-----------|---------------|
| design, architecture | 10 |
| development, analysis, research | 5 |
| review, 以及其他 | 3 |

**响应格式**：
```yaml
DispatchCognitionResponse:
  cognitions:
    - id: string
      type: string            # pattern | lesson | fact | template
      content: string         # 认知内容摘要
      confidence: float       # 置信度 0-1
      source:
        document_id: string    # 来源文档 ID
        document_title: string # 来源文档名称（人类可读）
        file_path: string     # 来源文件路径
        chunk_id: string       # 来源 chunk ID
  total: int
  has_more: bool
```

**认知携带方式**：

派发任务时，认知以结构化方式注入到任务上下文中，不修改 Agent 收到的任务描述内容：

```json
// Agent 收到的任务 Payload
{
  "task_id": "MAK-100",
  "title": "实现用户认证模块",
  "description": "...",
  "cognition_context": {
    "retrieved_at": "2026-04-08T16:55:00Z",
    "cognitions": [
      {
        "type": "pattern",
        "content": "认证模块采用 JWT + RefreshToken 模式，参考 nexus-vision.md 中的安全设计规范",
        "source": {
          "document_title": "doc-03-架构设计_00-platform-architecture.md",
          "file_path": "docs/03-架构设计/00-platform-architecture.md"
        }
      },
      {
        "type": "lesson",
        "content": "上一版本在此模块踩过坑：refresh token 续期时需要先验证旧 token 是否已加入黑名单",
        "source": {
          "document_title": "nexus-vision.md"
        }
      }
    ]
  }
}
```

**特点**：
- 同步调用，默认超时 3 秒
- 任务描述作为查询词，LLM 做语义召回
- 返回结果按相关性排序，最多 5 条
- 来源信息（文档名、路径）直接附带，Agent 可自行读取原文
- 降级时：返回空 cognitions，任务仍可正常派发

**与场景1（意图理解）的区别**：

| 维度 | 场景1：意图理解 | 场景5：认知抽取 |
|------|---------------|---------------|
| 时机 | 分解前 | 派发前 |
| 目的 | 指导怎么拆 | 告诉怎么做 |
| 内容 | 领域概念、任务模板 | 设计文档、最佳实践、教训 |
| 使用者 | Reins（分解算法） | Agent（执行者） |

### 2.4 调用策略决策矩阵

| 场景 | 同步/异步 | 超时 | 重试 | 降级 |
|------|----------|------|------|------|
| 意图理解 | 同步 | 5s | 2次 | 返回默认模板 |
| 智能体匹配 | 同步 | 2s | 1次 | 负载均衡 |
| 任务派发认知抽取 | 同步 | 3s | 1次 | 返回空列表，任务正常派发 |
| 执行监控 | 异步 | N/A | N/A | 静默忽略 |
| 认知回流 | 异步 | N/A | 3次 | 写入本地队列 |

### 2.5 调用入口设计

```python
# reins_grasp_caller.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import asyncio
import time

class CallType(Enum):
    SYNC = "sync"
    ASYNC_FIRE_FORGET = "async_fire_forget"
    ASYNC_CALLBACK = "async_callback"

class GraspCapability(Enum):
    INTENT_UNDERSTANDING = "intent_understanding"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    AGENT_MATCHING = "agent_matching"
    COGNITIVE_FEEDBACK = "cognitive_feedback"
    DISPATCH_COGNITION = "dispatch_cognition"  # 任务派发时认知抽取

@dataclass
class GraspCallRequest:
    capability: GraspCapability
    call_type: CallType
    payload: Dict[str, Any]
    timeout_seconds: float = 5.0
    retry_count: int = 0
    callback_url: Optional[str] = None

@dataclass
class GraspCallResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cache_hit: bool = False
    duration_ms: int = 0

class IReinsGraspCaller(ABC):
    """Reins 调用 Grasp 的接口定义"""
    
    @abstractmethod
    async def call_intent_understanding(
        self,
        user_goal: str,
        context: Dict[str, Any]
    ) -> GraspCallResponse:
        """意图理解 - 同步调用"""
        pass
    
    @abstractmethod
    async def call_agent_matching(
        self,
        task_requirements: Dict[str, Any],
        available_agents: List[Dict[str, Any]]
    ) -> GraspCallResponse:
        """智能体匹配 - 同步调用"""
        pass

    @abstractmethod
    async def call_dispatch_cognition(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        max_cognitions: int = 5
    ) -> GraspCallResponse:
        """任务派发时认知抽取 - 同步调用"""
        pass
    
    @abstractmethod
    async def send_cognitive_feedback(
        self,
        task_id: str,
        execution_result: Dict[str, Any],
        learnings: Dict[str, Any]
    ) -> bool:
        """认知回流 - 异步调用"""
        pass
    
    @abstractmethod
    async def send_execution_monitoring(
        self,
        task_id: str,
        execution_state: Dict[str, Any],
        callbacks: Dict[str, str]
    ) -> bool:
        """执行监控 - 异步调用"""
        pass
```

---

## 3. 缓存策略

### 3.1 缓存设计原则

| 原则 | 说明 |
|------|------|
| **TTL 分级** | 不同类型数据使用不同 TTL |
| **LRU 淘汰** | 缓存满时淘汰最少使用的条目 |
| **Key 规范** | 统一使用 hash(question + mode) 作为 key |
| **异步更新** | 缓存写入异步化，不阻塞主流程 |

### 3.2 缓存分级

| 缓存级别 | 数据类型 | TTL | 容量 | 说明 |
|---------|---------|-----|------|------|
| **L1 内存缓存** | 意图理解结果 | 5 分钟 | 1000 条 | 热点数据快速访问 |
| **L2 Redis 缓存** | 知识检索结果 | 30 分钟 | 10000 条 | 跨 Reins 实例共享 |
| **L3 持久缓存** | 领域认知模板 | 24 小时 | 无限 | Grasp 本地存储 |

### 3.3 缓存 Key 设计

```python
# cache_key_generator.py

import hashlib
import json

class CacheKeyGenerator:
    """缓存 Key 生成器"""
    
    @staticmethod
    def for_intent_understanding(user_goal: str, context_hash: str) -> str:
        """意图理解缓存 Key"""
        key_data = f"intent:{user_goal}:{context_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def for_agent_matching(task_req_hash: str, agents_hash: str) -> str:
        """智能体匹配缓存 Key"""
        key_data = f"match:{task_req_hash}:{agents_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def for_knowledge_query(question: str, mode: str, filters_hash: str) -> str:
        """知识检索缓存 Key"""
        key_data = f"knowledge:{question}:{mode}:{filters_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def for_domain_context(domain: str) -> str:
        """领域上下文缓存 Key"""
        key_data = f"domain:{domain}"
        return hashlib.md5(key_data.encode()).hexdigest()
```

### 3.4 缓存读写流程

```
请求进入
    │
    ▼
┌─────────────────┐
│  检查 L1 缓存   │ ──Hit──→ 返回结果（标记 cache_hit=true）
└────────┬────────┘
         │ Miss
         ▼
┌─────────────────┐
│  检查 L2 缓存   │ ──Hit──→ 返回结果 + 写入 L1（标记 cache_hit=true）
└────────┬────────┘
         │ Miss
         ▼
┌─────────────────┐
│  调用 Grasp     │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 成功     │ 失败
    ▼         ▼
┌─────────┐ ┌─────────┐
│ 写入 L2  │ │ 降级处理 │
│ + 写入L1 │ └─────────┘
└────┬────┘
     ▼
  返回结果
```

### 3.5 缓存失效策略

| 失效类型 | 触发条件 | 处理方式 |
|---------|---------|---------|
| **TTL 过期** | 到达 TTL | 自动淘汰 |
| **容量满** | LRU 淘汰 | 淘汰最少使用条目 |
| **主动失效** | Grasp 知识更新 | 通过事件通知 Reins |
| **版本变更** | 接口版本变化 | 全量失效 |

```python
# cache_invalidation.py

class CacheInvalidationStrategy:
    """缓存失效策略"""
    
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._register_handlers()
    
    def _register_handlers(self):
        """注册事件处理器"""
        self._event_bus.subscribe(
            "grasp.knowledge.updated",
            self._on_knowledge_updated
        )
        self._event_bus.subscribe(
            "grasp.domain.context_changed",
            self._on_domain_context_changed
        )
    
    async def _on_knowledge_updated(self, event):
        """知识更新事件"""
        domain = event.get("domain")
        if domain:
            # 失效相关领域缓存
            await self._invalidate_pattern(f"domain:{domain}*")
            await self._invalidate_pattern(f"knowledge:*:{domain}*")
    
    async def _on_domain_context_changed(self, event):
        """领域上下文变更事件"""
        domain = event.get("domain")
        if domain:
            # 失效领域上下文缓存
            await self._invalidate_pattern(f"domain:{domain}")
            # 失效意图理解缓存（涉及该领域）
            await self._invalidate_pattern(f"intent:*:{domain}*")
```

### 3.6 缓存配置

```yaml
# reins_grasp_cache.yaml

cache:
  l1:
    # L1 内存缓存配置
    enabled: true
    max_size: 1000
    ttl_seconds: 300  # 5 分钟
  
  l2:
    # L2 Redis 缓存配置
    enabled: true
    max_size: 10000
    ttl_seconds: 1800  # 30 分钟
    redis:
      host: "${REDIS_HOST}"
      port: 6379
      db: 0
      password: "${REDIS_PASSWORD}"
  
  l3:
    # L3 Grasp 本地持久缓存配置
    enabled: true
    ttl_seconds: 86400  # 24 小时
    # 由 Grasp 自身管理

invalidation:
  # 主动失效配置
  enabled: true
  event_subscription:
    - grasp.knowledge.updated
    - grasp.domain.context_changed
    - grasp.model.version_changed
```

---

## 4. 降级策略

### 4.1 降级层次定义

```
┌─────────────────────────────────────────────────────────────────┐
│                     Level 0: 完整服务                           │
│  Grasp 全部功能可用                                            │
│  - 意图理解：Grasp 分析用户目标                                 │
│  - 智能体匹配：Grasp 推荐最佳智能体                             │
│  - 知识检索：Grasp 提供领域知识                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (Grasp 响应 > 5s)
┌─────────────────────────────────────────────────────────────────┐
│                     Level 1: 降速服务                           │
│  Grasp 慢速响应，启用熔断                                       │
│  - 意图理解：返回缓存结果 + 异步补充                             │
│  - 智能体匹配：使用负载均衡                                     │
│  - 请求进入排队队列                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (Grasp 无响应)
┌─────────────────────────────────────────────────────────────────┐
│                     Level 2: 最小化服务                         │
│  仅缓存可用                                                    │
│  - 意图理解：返回默认任务模板                                   │
│  - 智能体匹配：轮询分配智能体                                   │
│  - 知识检索：返回缓存中的最后结果                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (完全不可用)
┌─────────────────────────────────────────────────────────────────┐
│                     Level 3: 服务降级                           │
│  Reins 自主决策                                                │
│  - 意图理解：Reins 使用内置启发式规则分解目标                   │
│  - 智能体匹配：基于负载和可用性的简单选择                       │
│  - 记录所有降级操作，后续补充 Grasp 分析                        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 降级决策规则

```python
# degradation_decider.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
import time
import logging

logger = logging.getLogger(__name__)

class DegradationLevel(Enum):
    FULL = 0           # 完整服务
    RATE_LIMITED = 1  # 降速服务
    CACHED_ONLY = 2   # 仅缓存
    DEGRADED = 3      # 服务降级

@dataclass
class DegradationState:
    level: DegradationLevel
    reason: str
    since: float
    consecutive_failures: int = 0
    last_attempt: Optional[float] = None

class DegradationDecider:
    """
    降级决策器
    根据 Grasp 响应状态决定降级策略
    """
    
    # 降级阈值配置
    SLOW_RESPONSE_THRESHOLD_MS = 5000    # 5 秒判定为慢响应
    FAILURE_THRESHOLD_FOR_CACHED = 3     # 3 次失败 -> CACHED_ONLY
    FAILURE_THRESHOLD_FOR_DEGRADED = 5  # 5 次失败 -> DEGRADED
    
    # 恢复检查间隔
    RECOVERY_CHECK_INTERVAL_SECONDS = 30
    
    def __init__(self):
        self._state = DegradationState(
            level=DegradationLevel.FULL,
            reason="initial",
            since=time.time()
        )
    
    @property
    def current_level(self) -> DegradationLevel:
        return self._state.level
    
    def should_attempt_grasp(self) -> bool:
        """是否应该尝试调用 Grasp"""
        if self._state.level == DegradationLevel.DEGRADED:
            # 检查是否应该尝试恢复
            elapsed = time.time() - (self._state.last_attempt or 0)
            if elapsed > self.RECOVERY_CHECK_INTERVAL_SECONDS:
                self._state.last_attempt = time.time()
                logger.info("Attempting Grasp recovery check")
                return True
            return False
        return True
    
    def record_response(self, duration_ms: int, success: bool, error: Optional[str] = None):
        """记录 Grasp 响应状态"""
        if success and duration_ms < self.SLOW_RESPONSE_THRESHOLD_MS:
            # 成功且快速响应
            self._record_success()
        elif success and duration_ms >= self.SLOW_RESPONSE_THRESHOLD_MS:
            # 成功但慢速响应
            self._record_slow_response()
        else:
            # 失败
            self._record_failure(error)
    
    def _record_success(self):
        """记录成功响应"""
        old_level = self._state.level
        self._state.consecutive_failures = 0
        
        if old_level != DegradationLevel.FULL:
            logger.info(f"Grasp recovered, upgrading from {old_level} to FULL")
            self._state.level = DegradationLevel.FULL
            self._state.reason = "service_recovered"
    
    def _record_slow_response(self):
        """记录慢速响应"""
        old_level = self._state.level
        
        if old_level == DegradationLevel.FULL:
            # 首次慢速，降级到降速服务
            self._state.level = DegradationLevel.RATE_LIMITED
            self._state.reason = "slow_response"
            logger.warning("Grasp slow response detected, degrading to RATE_LIMITED")
    
    def _record_failure(self, error: Optional[str]):
        """记录失败响应"""
        self._state.consecutive_failures += 1
        self._state.last_attempt = time.time()
        
        old_level = self._state.level
        
        if self._state.consecutive_failures >= self.FAILURE_THRESHOLD_FOR_DEGRADED:
            self._state.level = DegradationLevel.DEGRADED
            self._state.reason = f"consecutive_failures:{self._state.consecutive_failures}"
            logger.error(f"Grasp consecutive failures reached {self._state.consecutive_failures}, degrading to DEGRADED")
        elif self._state.consecutive_failures >= self.FAILURE_THRESHOLD_FOR_CACHED:
            if self._state.level != DegradationLevel.CACHED_ONLY:
                self._state.level = DegradationLevel.CACHED_ONLY
                self._state.reason = f"consecutive_failures:{self._state.consecutive_failures}"
                logger.warning(f"Grasp failures reached {self._state.consecutive_failures}, degrading to CACHED_ONLY")
        
        if old_level != self._state.level:
            logger.warning(f"Grasp degradation level changed: {old_level.name} -> {self._state.level.name}")
```

### 4.3 降级响应生成

```python
# fallback_response.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class FallbackResponse:
    """降级响应"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class FallbackResponseGenerator:
    """降级响应生成器"""
    
    # 默认任务模板
    DEFAULT_TASK_TEMPLATES = [
        {"type": "analysis", "description": "执行分析任务", "capabilities": ["analysis"]},
        {"type": "development", "description": "执行开发任务", "capabilities": ["coding"]},
        {"type": "review", "description": "执行审查任务", "capabilities": ["review"]},
        {"type": "deployment", "description": "执行部署任务", "capabilities": ["deployment"]},
    ]
    
    def generate_intent_fallback(self, user_goal: str) -> FallbackResponse:
        """
        生成意图理解的降级响应
        使用启发式规则分解目标
        """
        goal_lower = user_goal.lower()
        
        # 简单的关键词匹配
        if "分析" in user_goal or "analyze" in goal_lower:
            suggested_type = "analysis"
        elif "开发" in user_goal or "implement" in goal_lower or "build" in goal_lower:
            suggested_type = "development"
        elif "审查" in user_goal or "review" in goal_lower or "检查" in user_goal:
            suggested_type = "review"
        elif "部署" in user_goal or "deploy" in goal_lower:
            suggested_type = "deployment"
        else:
            suggested_type = "general"
        
        # 返回默认模板
        matching_templates = [
            t for t in self.DEFAULT_TASK_TEMPLATES 
            if t["type"] == suggested_type
        ] or [{"type": "general", "description": "执行任务", "capabilities": []}]
        
        logger.warning(f"Using fallback intent understanding for goal: {user_goal[:50]}...")
        
        return FallbackResponse(
            answer=f"目标分解（降级模式）：{suggested_type}类型任务",
            confidence=0.3,  # 低置信度
            sources=[],
            metadata={
                "fallback": True,
                "original_goal": user_goal,
                "suggested_type": suggested_type,
                "templates": matching_templates
            }
        )
    
    def generate_agent_matching_fallback(
        self,
        task_requirements: Dict[str, Any],
        available_agents: List[Dict[str, Any]]
    ) -> FallbackResponse:
        """
        生成智能体匹配的降级响应
        使用简单的负载均衡选择
        """
        if not available_agents:
            return FallbackResponse(
                answer="无可用智能体",
                confidence=0.0,
                sources=[],
                metadata={"fallback": True, "error": "no_agents_available"}
            )
        
        # 按负载排序，选择最空闲的
        sorted_agents = sorted(
            available_agents,
            key=lambda a: a.get("current_load", 100)
        )
        
        best_agent = sorted_agents[0]
        
        logger.warning(f"Using fallback agent matching, selected: {best_agent.get('agent_id')}")
        
        return FallbackResponse(
            answer=f"选择智能体（降级模式）：{best_agent.get('agent_id')}",
            confidence=0.4,
            sources=[],
            metadata={
                "fallback": True,
                "selected_agent": best_agent,
                "all_agents": available_agents,
                "selection_method": "load_balancing"
            }
        )
```

### 4.4 降级流程集成

```python
# reins_grasp_integration.py

class ReinsGraspIntegration:
    """
    Reins-Grasp 集成主类
    整合调用、缓存、降级策略
    """
    
    def __init__(
        self,
        grasp_client: IGraspClient,
        cache_manager: 'CacheManager',
        degradation_decider: 'DegradationDecider',
        fallback_generator: 'FallbackResponseGenerator'
    ):
        self._grasp = grasp_client
        self._cache = cache_manager
        self._degradation = degradation_decider
        self._fallback = fallback_generator
    
    async def understand_intent(
        self,
        user_goal: str,
        context: Dict[str, Any]
    ) -> GraspCallResponse:
        """
        意图理解入口
        整合缓存 + 调用 + 降级
        """
        # 1. 检查降级决策
        if not self._degradation.should_attempt_grasp():
            logger.info("Grasp degraded, using fallback")
            return await self._fallback_intent_understanding(user_goal, context)
        
        # 2. 检查缓存
        cache_key = CacheKeyGenerator.for_intent_understanding(
            user_goal,
            self._hash_context(context)
        )
        cached = await self._cache.get(cache_key)
        if cached:
            return GraspCallResponse(
                success=True,
                data=cached,
                cache_hit=True
            )
        
        # 3. 尝试调用 Grasp
        start_time = time.time()
        try:
            response = await self._grasp.call_intent_understanding(
                user_goal=user_goal,
                context=context
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 4. 记录响应状态
            self._degradation.record_response(duration_ms, success=True)
            
            # 5. 写入缓存
            if response.success:
                await self._cache.set(cache_key, response.data)
            
            return GraspCallResponse(
                success=True,
                data=response.data,
                cache_hit=False,
                duration_ms=duration_ms
            )
            
        except GraspCallError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._degradation.record_response(duration_ms, success=False, error=str(e))
            
            # 6. 降级处理
            return await self._fallback_intent_understanding(user_goal, context)
    
    async def _fallback_intent_understanding(
        self,
        user_goal: str,
        context: Dict[str, Any]
    ) -> GraspCallResponse:
        """意图理解降级处理"""
        # 尝试返回缓存（即使过期）
        cached = await self._cache.get_stale()
        if cached:
            return GraspCallResponse(
                success=True,
                data=cached,
                cache_hit=True,
                metadata={"degraded": True, "stale": True}
            )
        
        # 使用启发式降级响应
        fallback_response = self._fallback.generate_intent_fallback(user_goal)
        
        return GraspCallResponse(
            success=True,
            data={
                "intent": {
                    "type": fallback_response.metadata.get("suggested_type", "general"),
                    "confidence": fallback_response.confidence
                },
                "suggested_tasks": fallback_response.metadata.get("templates", []),
                "fallback_mode": True
            },
            cache_hit=False,
            metadata={"degraded": True, "fallback": True}
        )
```

### 4.5 降级配置

```yaml
# reins_grasp_degradation.yaml

degradation:
  # 降级阈值配置
  thresholds:
    slow_response_ms: 5000      # 慢响应阈值（毫秒）
    failure_for_cached: 3       # 失败次数 -> CACHED_ONLY
    failure_for_degraded: 5     # 失败次数 -> DEGRADED
  
  # 恢复检查
  recovery:
    check_interval_seconds: 30  # 恢复检查间隔
    attempts_before_full: 3     # 成功次数 -> FULL
  
  # 降级响应配置
  fallback:
    intent_understanding:
      enabled: true
      use_heuristics: true      # 使用启发式规则
      use_stale_cache: true     # 允许使用过期缓存
      default_templates: true    # 返回默认任务模板
    
    agent_matching:
      enabled: true
      selection_method: "load_balancing"  # 降级时使用负载均衡
      fallback_to_round_robin: true  # 回退到轮询
    
    cognitive_feedback:
      enabled: true
      queue_locally: true       # 本地队列稍后重试
      max_queue_size: 1000
```

---

## 5. API 接口设计

### 5.1 Reins 调用 Grasp 的 API 端点

```yaml
# Reins -> Grasp 的内部调用 API

paths:
  /api/v1/grasp/intent:
    post:
      summary: 意图理解
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IntentRequest'
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IntentResponse'
        503:
          description: Grasp 降级
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DegradedResponse'

  /api/v1/grasp/agent-match:
    post:
      summary: 智能体匹配
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AgentMatchRequest'
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AgentMatchResponse'

  /api/v1/grasp/feedback:
    post:
      summary: 认知回流
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CognitiveFeedbackRequest'
      responses:
        202:
          description: 已接受（异步处理）

  /api/v1/grasp/dispatch-cognition:
    post:
      summary: 任务派发时认知抽取
      description: 在任务正式派发给 Agent 之前，查询相关认知并随任务一起下发
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DispatchCognitionRequest'
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DispatchCognitionResponse'
        503:
          description: Grasp 降级（返回空列表，任务仍正常派发）

  /api/v1/grasp/health:
    get:
      summary: Grasp 健康检查
      responses:
        200:
          description: 健康
        503:
          description: 不可用

components:
  schemas:
    IntentRequest:
      type: object
      required:
        - user_goal
      properties:
        user_goal:
          type: string
          description: 用户目标
        context:
          type: object
          properties:
            project_id:
              type: string
            agent_capabilities:
              type: array
              items:
                type: string
        options:
          type: object
          properties:
            max_tasks:
              type: integer
              default: 10
            include_templates:
              type: boolean
              default: true

    IntentResponse:
      type: object
      properties:
        intent:
          type: object
          properties:
            type:
              type: string
            confidence:
              type: number
            entities:
              type: array
        domain_context:
          type: object
        suggested_tasks:
          type: array
        cache_key:
          type: string

    AgentMatchRequest:
      type: object
      required:
        - task_requirements
        - available_agents
      properties:
        task_requirements:
          type: object
        available_agents:
          type: array
        context:
          type: object

    AgentMatchResponse:
      type: object
      properties:
        recommendations:
          type: array
        fallback_agents:
          type: array
        cache_key:
          type: string

    DispatchCognitionRequest:
      type: object
      required:
        - task
      properties:
        task:
          type: object
          properties:
            id:
              type: string
            title:
              type: string
            description:
              type: string
            type:
              type: string
            context:
              type: object
              properties:
                project:
                  type: string
                domain:
                  type: string
        options:
          type: object
          properties:
            max_cognitions:
              type: integer
              default: 5
            include_sources:
              type: boolean
              default: true

    DispatchCognitionResponse:
      type: object
      properties:
        cognitions:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              type:
                type: string
              content:
                type: string
              confidence:
                type: number
              source:
                type: object
                properties:
                  document_id:
                    type: string
                  document_title:
                    type: string
                  file_path:
                    type: string
                  chunk_id:
                    type: string
        total:
          type: integer
        has_more:
          type: boolean

    CognitiveFeedbackRequest:
      type: object
      required:
        - task_id
        - execution_result
      properties:
        task_id:
          type: string
        execution_result:
          type: object
        learnings:
          type: object
        metadata:
          type: object

    DegradedResponse:
      type: object
      properties:
        status:
          type: string
          example: degraded
        message:
          type: string
        fallback_data:
          type: object
        confidence:
          type: number
```

### 5.2 健康检查与状态同步

```yaml
paths:
  /api/v1/grasp/health/detailed:
    get:
      summary: 详细健康检查（包含降级状态）
      responses:
        200:
          description: 健康状态详情
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [healthy, degraded, unhealthy]
                  grasp_service:
                    status: string
                    latency_ms: integer
                    last_success: string
                  cache:
                    l1_hit_rate: number
                    l2_hit_rate: number
                  degradation:
                    current_level: integer
                    reason: string
                    since: string
```

---

## 6. 监控指标

### 6.1 关键指标定义

| 指标名称 | 类型 | 描述 | 告警阈值 |
|---------|------|------|----------|
| `reins_grasp_call_total` | Counter | 调用总数 | - |
| `reins_grasp_call_duration_ms` | Histogram | 调用耗时分布 | P99 > 5s |
| `reins_grasp_call_errors_total` | Counter | 错误总数（按错误类型） | > 10/min |
| `reins_grasp_cache_hit_ratio` | Gauge | 缓存命中率 | < 0.6 |
| `reins_grasp_degradation_level` | Gauge | 当前降级等级 | > 0 |
| `reins_grasp_fallback_total` | Counter | 降级响应次数 | > 5/min |

### 6.2 监控告警配置

```yaml
# alerting.yaml

alerts:
  - name: grasp_high_latency
    condition: reins_grasp_call_duration_ms.p99 > 5000
    severity: warning
    message: "Grasp P99 延迟超过 5 秒"
  
  - name: grasp_low_cache_hit_rate
    condition: reins_grasp_cache_hit_ratio < 0.6
    severity: warning
    message: "Grasp 缓存命中率低于 60%"
  
  - name: grasp_degraded
    condition: reins_grasp_degradation_level > 0
    severity: critical
    message: "Grasp 进入降级模式"
  
  - name: grasp_fallback_high
    condition: reins_grasp_fallback_total > 5
    severity: warning
    message: "Grasp 降级响应次数过多"
```

---

## 7. 部署配置

### 7.1 配置参数

```yaml
# reins_grasp_config.yaml

reins_grasp:
  # Grasp 服务地址
  grasp_url: "${GRASP_SERVICE_URL:-http://grasp:8000}"
  
  # 超时配置
  timeout:
    connect_seconds: 5
    read_seconds: 30
    total_seconds: 60
  
  # 重试配置
  retry:
    max_attempts: 3
    initial_delay_seconds: 1.0
    max_delay_seconds: 30.0
    jitter_percent: 20
  
  # 调用配置
  calling:
    intent_understanding:
      timeout_seconds: 5
      retry_count: 2
    agent_matching:
      timeout_seconds: 2
      retry_count: 1
    cognitive_feedback:
      async_enabled: true
      queue_size: 1000
    execution_monitoring:
      async_enabled: true
      batch_size: 10
```

### 7.2 环境变量

```bash
# Grasp 服务配置
export GRASP_SERVICE_URL="http://grasp:8000"

# Redis 缓存配置
export REDIS_HOST="redis"
export REDIS_PORT=6379
export REDIS_PASSWORD=""

# 日志配置
export REINS_GRASP_LOG_LEVEL="INFO"
```

---

## 8. 版本与变更

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-04-04 | 初始版本 | 谷子 |
| v1.1 | 2026-04-08 | 新增场景5：任务派发时的认知抽取 | 刚子 |

---

## 9. 已明确事项

以下事项在 v1.0 设计中已明确：

| 事项 | 结论 |
|------|------|
| 通信协议 | REST (HTTP/JSON) |
| 服务发现 | 通过配置中心或环境变量指定 Grasp URL |
| 认证授权 | 内部服务间调用暂不需要认证 |
| 降级策略 | 场景5降级时返回空列表，任务正常派发 |

## 10. 待明确事项

| # | 事项 | 状态 | 结论/备注 |
|---|------|------|----------|
| 1 | GraphRAG 查询模式选择 | ✅ 已明确 | local search（语义相似度召回） |
| 2 | 认知数量上限 | ✅ 已明确 | 分档设置（见下） |
| 3 | 来源文档安全 | ⏳ 待讨论 | 鉴权问题后续集中讨论 |

### 10.1 认知数量分档策略

| 档位 | 数量 | 适用任务类型 | 典型内容构成 |
|------|------|-------------|------------|
| **简洁** | 3 条 | review、simple task | 1 pattern + 1 lesson + 1 fact |
| **标准** | 5 条 | development、analysis、research | 2 pattern + 2 lesson + 1 fact |
| **详细** | 8-10 条 | design、architecture | 3 pattern + 3 lesson + 2 fact + 2 template |

**档位判定规则**：
```python
def get_cognition_limit(task_type: str) -> int:
    if task_type in ("design", "architecture"):
        return 10
    elif task_type in ("development", "analysis", "research"):
        return 5
    else:
        return 3
```

**设计原则**：
- 认知塞入 agent context，context 越长推理成本越高、关注度越分散
- 捞最相关的少数几条性价比最高，不需要贪多


---

## MAK-77: Grasp 集成任务

# MAK-77: Grasp 调用集成设计

**版本**: v1.0  
**作者**: 谷子  
**日期**: 2026-04-03  
**状态**: 设计完成  
**Issue**: MAK-77  

---

## 1. 概述

本文档设计 Nexus Reins（御）如何调用 Grasp（悟）认知系统，包括调用策略、缓存策略、降级策略和错误处理机制。

### 1.1 设计目标

| 目标 | 说明 |
|------|------|
| **高效调用** | Reins 任务执行时能快速获取认知支持 |
| **容错可靠** | Grasp 不可用时 Reins 仍能继续工作 |
| **认知统一** | 所有 Reins Agent 共享同一套认知体系 |
| **低延迟** | 认知检索延迟 ≤ 100ms（P95） |

### 1.2 架构关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Reins（御 - 驾驭层）                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Agent A    │  │  Agent B    │  │  Agent N    │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│              ┌─────────────────────────┐                     │
│              │   Reins Agent Adapter   │                     │
│              │  (Grasp 调用封装层)        │                     │
│              └──────────┬──────────────┘                     │
│                         │                                     │
│                         ▼                                     │
└─────────────────────────┼─────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Grasp（悟 - 认知层）                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Grasp Skill / Agent                      │   │
│  │  (认知检索、注入、注册、更新)                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                    │
│                          ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              本地知识库                               │   │
│  │  - cognitions.jsonl（认知条目）                        │   │
│  │  - vector.index（向量索引）                           │   │
│  │  - keyword.index（关键词索引）                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 调用架构

### 2.1 调用模式

Reins 调用 Grasp 采用 **Agent 内嵌 Skill** 模式：

```
┌─────────────────────────────────────────────────────────────┐
│  Reins Agent 实例                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Grasp Skill（内嵌）                                 │    │
│  │  - register()  [Reins 初始化时使用]                    │    │
│  │  - inject()    [Reins 任务执行后使用]                  │    │
│  │  - retrieve()  [Reins 任务执行中频繁使用]             │    │
│  │  - update()    [Reins 认知更新时使用]                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│              本地知识库（JSONL + 向量索引）                    │
└─────────────────────────────────────────────────────────────┘
```

**为什么采用内嵌模式**：
- ✅ **低延迟**：本地调用，无需网络往返
- ✅ **高可用**：不依赖外部服务
- ✅ **易部署**：单 Agent 即可独立运行
- ⚠️ **数据同步**：需要通过 A2A Hub 同步多 Agent 认知

### 2.2 调用接口

Reins Agent 通过以下方式调用 Grasp：

#### 2.2.1 retrieve - 认知检索（高频）

**使用场景**：
- 任务拆解前：检索"任务分解最佳实践"
- 工具选择时：检索"xxx 工具使用经验"
- 错误处理时：检索"xxx 错误处理模式"
- 质量验收时：检索"xxx 质量标准"

**接口定义**：

```typescript
interface GraspRetrieveOptions {
  // 查询文本（必填）
  query: string;
  
  // 过滤条件
  type?: ('fact' | 'pattern' | 'lesson' | 'meta')[];
  tags?: string[];
  min_confidence?: number;  // 默认 0.7
  min_quality?: number;     // 默认 0.6
  
  // 分页
  limit?: number;  // 默认 10，最大 50
  offset?: number;
}

interface GraspRetrieveResult {
  items: CognitionItem[];
  total: number;
  query_time_ms: number;
}
```

#### 2.2.2 inject - 认知注入（低频）

**使用场景**：
- 任务执行完成后：注入"任务执行经验"
- 发现新模式：注入"新模式认知"
- 修复错误后：注入"错误修复模式"

**接口定义**：

```typescript
interface GraspInjectOptions {
  type: 'fact' | 'pattern' | 'lesson' | 'meta';
  content: string;
  source: {
    agent_id: string;
    task_id?: string;
    channel: 'execution_feedback' | 'manual' | 'auto_learn';
  };
  tags?: string[];
  confidence?: number;  // 默认 0.8
}
```

#### 2.2.3 register - 认知注册（初始化）

**使用场景**：
- Reins 启动时：注册初始认知模式
- 领域扩展时：注册新认知类型

**接口定义**：

```typescript
interface GraspRegisterOptions {
  cognitionTypes?: CognitionType[];
  tagSystem?: TagSystem;
  reviewRules?: ReviewRule[];
}
```

#### 2.2.4 update - 认知更新（维护）

**使用场景**：
- 认知过时：更新"xx 工具配置参数"
- 认知修正：修正"xx 错误处理模式"

---

## 3. 调用策略

### 3.1 缓存策略

采用 **三层缓存** 机制，平衡性能与一致性：

```
┌─────────────────────────────────────────────────────────────┐
│  第一层：内存缓存（L1 Cache）                                │
│  - 缓存内容：最近检索的认知结果                              │
│  - 缓存大小：LRU 100 条                                      │
│  - 过期策略：5 分钟                                          │
│  - 命中预期：60%~80%                                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  第二层：本地索引缓存（L2 Cache）                             │
│  - 缓存内容：向量索引 + 关键词索引                           │
│  - 缓存大小：全量索引                                       │
│  - 过期策略：索引更新时失效                                 │
│  - 命中预期：15%~25%                                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  第三层：远程 Grasp 服务（Source of Truth）                   │
│  - 缓存内容：完整认知库                                      │
│  - 同步策略：A2A Hub 推送 + 定期拉取                          │
│  - 一致性：最终一致性                                        │
└─────────────────────────────────────────────────────────────┘
```

#### 3.1.1 L1 内存缓存实现

```typescript
class GraspCache {
  private l1Cache: Map<string, CognitionResult>;
  private l1TTL = 5 * 60 * 1000; // 5 分钟
  
  async retrieve(query: string): Promise<CognitionResult> {
    const cacheKey = this.generateCacheKey(query);
    
    // 检查 L1 缓存
    const cached = this.l1Cache.get(cacheKey);
    if (cached && !this.isExpired(cached)) {
      return cached;
    }
    
    // 查询本地索引
    const result = await this.queryLocalIndex(query);
    
    // 写入 L1 缓存
    this.l1Cache.set(cacheKey, {
      data: result,
      timestamp: Date.now()
    });
    
    return result;
  }
  
  private generateCacheKey(query: string): string {
    // 归一化查询后生成哈希
    const normalized = query.toLowerCase().trim();
    return crypto.createHash('md5').update(normalized).digest('hex');
  }
}
```

#### 3.1.2 缓存失效策略

| 触发条件 | 操作 |
|---------|------|
| 认知注入成功 | 清空 L1 相关缓存 |
| 认知更新成功 | 清空 L1 相关缓存 |
| A2A Hub 收到同步 | 刷新 L1 缓存 |
| 定时任务（每小时） | 清理过期缓存 |

### 3.2 降级策略

Grasp 不可用时，Reins 采用以下降级策略：

#### 3.2.1 降级等级

| 等级 | 条件 | 行为 |
|------|------|------|
| **P0 - 正常** | Grasp 服务可用 | 正常检索认知 |
| **P1 - 缓存模式** | L1 缓存命中率高（>70%） | 仅使用缓存结果，忽略未命中 |
| **P2 - 本地模式** | Grasp 完全不可用 | 使用本地已加载的认知，不查询远程 |
| **P3 - 无认知模式** | 本地认知库为空 | 不检索认知，继续执行任务（带告警） |

#### 3.2.2 降级流程图

```
Grasp 调用请求
     │
     ▼
检查 Grasp 服务状态
     │
     ├─正常 ──────────────────────▶ 正常检索
     │
     └─异常 ──────────────────────▶ 检查降级等级
               │
               ├─P1 缓存模式 ──▶ 仅返回缓存结果
               │               （未命中返回空）
               │
               ├─P2 本地模式 ──▶ 查询本地索引
               │               （可返回部分结果）
               │
               └─P3 无认知模式 ─▶ 跳过认知检索
                               （记录告警日志）
```

#### 3.2.3 降级实现

```typescript
class GraspClient {
  private degradationLevel: DegradationLevel = 'normal';
  private lastErrorTime: number | null = null;
  
  async retrieve(query: string): Promise<CognitionResult> {
    // 检查服务状态
    if (!await this.isServiceHealthy()) {
      return this.handleDegradation(query);
    }
    
    // 正常检索
    return await this.normalRetrieve(query);
  }
  
  private async handleDegradation(query: string): Promise<CognitionResult> {
    switch (this.degradationLevel) {
      case 'cache_only':
        // 仅返回缓存结果
        const cached = await this.cache.get(query);
        return cached || { items: [], total: 0 };
      
      case 'local_only':
        // 查询本地索引
        return await this.queryLocalIndex(query);
      
      case 'no_cognition':
        // 记录告警
        logger.warn('Grasp unavailable, no cognition available', { query });
        return { items: [], total: 0 };
    }
  }
  
  private async isServiceHealthy(): Promise<boolean> {
    // 健康检查：过去 5 分钟内无错误
    if (!this.lastErrorTime) return true;
    return (Date.now() - this.lastErrorTime) > 5 * 60 * 1000;
  }
}
```

### 3.3 重试策略

#### 3.3.1 重试场景

| 错误类型 | 是否重试 | 重试次数 | 重试间隔 |
|---------|---------|---------|---------|
| 网络超时 | 是 | 3 次 | 指数退避（1s, 2s, 4s） |
| 连接拒绝 | 是 | 3 次 | 指数退避（1s, 2s, 4s） |
| 服务不可用 | 是 | 5 次 | 指数退避（1s, 2s, 4s, 8s, 16s） |
| 查询超时 | 是 | 2 次 | 固定间隔（2s） |
| 认证失败 | 否 | 0 次 | - |
| 权限拒绝 | 否 | 0 次 | - |
| 参数错误 | 否 | 0 次 | - |

#### 3.3.2 重试实现

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = defaultRetryOptions
): Promise<T> {
  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt < options.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      // 判断是否可重试
      if (!isRetryableError(error)) {
        throw error;
      }
      
      // 计算重试间隔
      const delay = calculateBackoff(attempt, options);
      
      if (attempt < options.maxRetries - 1) {
        await sleep(delay);
      }
    }
  }
  
  throw new RetryExhaustedError('Max retries exceeded', lastError);
}

// 使用示例
const result = await withRetry(
  () => graspClient.retrieve(query),
  {
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
    multiplier: 2
  }
);
```

---

## 4. 错误处理

### 4.1 错误分类

| 错误类型 | 错误码 | 说明 | 处理策略 |
|---------|--------|------|---------|
| **查询错误** | QUERY_INVALID | 查询参数无效 | 返回错误，不重试 |
| **检索错误** | RETRIEVE_FAILED | 检索失败 | 降级到缓存模式 |
| **注入错误** | INJECT_FAILED | 注入失败 | 记录日志，继续任务 |
| **同步错误** | SYNC_FAILED | 认知同步失败 | 标记待同步，继续任务 |
| **服务错误** | SERVICE_UNAVAILABLE | Grasp 服务不可用 | 降级策略 |

### 4.2 错误恢复

```typescript
class GraspErrorHandler {
  async handleRetrieveError(error: Error, query: string): Promise<CognitionResult> {
    logger.error('Grasp retrieve error', { error, query });
    
    if (error.code === 'SERVICE_UNAVAILABLE') {
      // 触发降级
      this.client.enterDegradationMode('local_only');
      
      // 尝试本地检索
      return await this.client.queryLocalIndex(query);
    }
    
    if (error.code === 'QUERY_INVALID') {
      // 返回空结果
      return { items: [], total: 0 };
    }
    
    // 其他错误：记录并返回缓存
    return await this.client.cache.get(query) || { items: [], total: 0 };
  }
}
```

---

## 5. 性能优化

### 5.1 批量检索

对于需要同时检索多个认知条目的场景，提供批量检索接口：

```typescript
interface BatchRetrieveOptions {
  queries: string[];
  options?: RetrieveOptions;
}

interface BatchRetrieveResult {
  results: Map<string, CognitionResult>;
  timings: Map<string, number>; // 每个查询的耗时
}

async function batchRetrieve(options: BatchRetrieveOptions): Promise<BatchRetrieveResult> {
  const results = new Map<string, CognitionResult>();
  const timings = new Map<string, number>();
  
  // 合并相似查询
  const groupedQueries = groupSimilarQueries(options.queries);
  
  // 批量执行
  for (const [representative, queryList] of groupedQueries) {
    const startTime = Date.now();
    const result = await retrieve(representative, options.options);
    const duration = Date.now() - startTime;
    
    // 分配结果给所有相似查询
    for (const query of queryList) {
      results.set(query, result);
      timings.set(query, duration);
    }
  }
  
  return { results, timings };
}
```

### 5.2 预加载认知

Reins Agent 启动时预加载常用认知：

```typescript
class GraspPreloader {
  private commonQueries = [
    '任务分解最佳实践',
    '工具使用经验',
    '错误处理模式',
    '质量标准',
    '领域知识',
  ];
  
  async preload(): Promise<void> {
    logger.info('Preloading common cognitions...');
    
    for (const query of this.commonQueries) {
      try {
        await this.client.retrieve(query, { limit: 5 });
      } catch (error) {
        logger.warn('Failed to preload cognition', { query, error });
      }
    }
    
    logger.info('Preloading completed');
  }
}
```

### 5.3 异步注入

认知注入采用异步方式，不阻塞任务执行：

```typescript
async function injectCognition(options: GraspInjectOptions): Promise<void> {
  // 异步注入，不等待结果
  injectPromise = graspClient.inject(options)
    .catch(error => {
      logger.error('Async cognition injection failed', { error });
    });
  
  return; // 立即返回，不等待注入完成
}
```

---

## 6. 监控与告警

### 6.1 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| `grasp.retrieve.latency.p95` | 检索延迟 P95 | > 200ms |
| `grasp.retrieve.hit_rate` | 缓存命中率 | < 60% |
| `grasp.retrieve.errors` | 检索错误次数 | > 10 次/分钟 |
| `grasp.inject.latency.p95` | 注入延迟 P95 | > 500ms |
| `grasp.degradation.count` | 降级次数 | > 5 次/小时 |
| `grasp.sync.failed` | 同步失败次数 | > 0 次/小时 |

### 6.2 日志规范

```typescript
// 正常检索日志
logger.info('Grasp retrieve', {
  query: query,
  result_count: result.items.length,
  latency_ms: result.query_time_ms,
  cache_hit: result.from_cache
});

// 错误日志
logger.error('Grasp retrieve error', {
  query: query,
  error: error.message,
  error_code: error.code,
  attempt: attempt
});

// 降级日志
logger.warn('Grasp degradation', {
  from_level: previous_level,
  to_level: current_level,
  reason: error.message
});
```

---

## 7. 实现计划

### 7.1 Phase 1 - MVP（本周）

- [ ] 实现 Grasp Client 基础封装
- [ ] 实现 L1 内存缓存
- [ ] 实现基本降级策略
- [ ] 实现重试机制
- [ ] 实现错误处理

### 7.2 Phase 2 - 优化（下周）

- [ ] 实现批量检索
- [ ] 实现预加载机制
- [ ] 实现异步注入
- [ ] 完善监控告警

### 7.3 Phase 3 - 完善（下下周）

- [ ] 实现 A2A 认知同步
- [ ] 实现认知版本管理
- [ ] 实现认知质量评估
- [ ] 性能测试和优化

---

## 8. 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Grasp 服务长时间不可用 | 高 | 中 | 降级策略保证基本功能 |
| 缓存不一致导致认知过时 | 中 | 中 | 定期同步 + 版本号机制 |
| 检索延迟过高影响任务执行 | 中 | 低 | 批量检索 + 预加载优化 |
| 认知注入失败导致经验丢失 | 低 | 中 | 异步注入 + 重试机制 |

---

## 9. 附录

### 9.1 参考资料

- [Grasp Skill Design](skills/grasp/Skill.md)
- [Reins Architecture](docs/03-总体架构/02-reins-architecture.md)
- [A2A Protocol](docs/03-总体架构/07-interface-architecture.md)

### 9.2 术语表

| 术语 | 说明 |
|------|------|
| Grasp | 悟 - 认知层，提供认知检索和注入 |
| Reins | 御 - 驾驭层，调用 Grasp 获取认知支持 |
| A2A | Agent-to-Agent，智能体间通信协议 |
| L1/L2 Cache | 一级/二级缓存 |
| P0-P3 | 降级等级 |

---

**修订历史**：

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-04-03 | 初始版本 | 谷子 |

---

*本文档设计完成，待实现*
