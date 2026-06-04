# Nexus Grasp-GLG 集成设计方案

**版本**: v1.0  
**日期**: 2026-04-03  
**负责人**: 麻子

---

## 1. 背景与目标

### 1.1 集成背景

Grasp（悟）是 Nexus 平台的认知层，负责本体建模和知识管理。GLG（GraphRAG-LangExtract-GraphRAG）是 Grasp 的核心能力引擎，负责从文档中提取结构化知识并构建知识图谱。

当前 GLG 是独立运行的 Python Pipeline，需要集成到 Nexus Grasp 体系中，使其能够：
- 被 Grasp Agent 调用
- 与其他 Grasp 组件（知识验证、信任评估等）协作
- 通过 Reins 可见可操纵

### 1.2 集成目标

| 目标 | 描述 | 优先级 |
|------|------|--------|
| API 接口标准化 | GLG 暴露的 FastAPI 接口与 Nexus 内部接口对齐 | P0 |
| 错误处理机制 | 各类 GLG 故障的优雅处理 | P0 |
| 降级策略 | GLG 不可用时的 fallback 机制 | P0 |
| 可观测性 | GLG 执行过程的可见性 | P1 |
| 会话管理 | GLG 长时任务的取消和恢复 | P1 |

### 1.3 非目标

- 不修改 GLG 内部实现（GLG 保持独立）
- 不将 GLG 重构为微服务（通过 API 远程调用）
- 不实现多 GLG 实例的负载均衡

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    Nexus Grasp                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          Grasp Agent (认知协调层)                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │
│  │  │ 知识请求路由 │  │  知识验证   │  │ 信任评估   │  │ 反馈路由    │        │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │   │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────────────┘   │
│            │                │                │                │                      │
│  ┌─────────┴────────────────┴────────────────┴────────────────┴────────────────┐   │
│  │                         Grasp Core API (统一入口)                            │   │
│  └──────────────────────────────────┬──────────────────────────────────────────┘   │
└─────────────────────────────────────┼─────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │     GLG Adapter (适配器层)        │
                    │  - 接口转换                      │
                    │  - 错误处理                      │
                    │  - 降级逻辑                      │
                    │  - 结果缓存                      │
                    └─────────────────┬─────────────────┘
                                      │ HTTP/gRPC
                                      │
┌─────────────────────────────────────┴─────────────────────────────────────────────┐
│                              GLG Pipeline (独立服务)                                │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  Stage 1      │  │  Stage 2      │  │  Stage 3      │  │   FastAPI     │       │
│  │  GraphRAG     │→│  LangExtract   │→│  BYOG Build   │  │   Interface   │       │
│  │  Discovery    │  │  Extraction   │  │  Query        │  │               │       │
│  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 职责 | 位置 |
|------|------|------|
| Grasp Agent | 协调知识流、调用 Grasp Core API | Nexus |
| Grasp Core API | 统一入口、路由、权限 | Nexus |
| GLG Adapter | GLG 接口适配、错误处理、降级 | Nexus |
| GLG Pipeline | 文档处理、知识提取 | 独立 Python |

### 2.3 数据流

```
用户/Agent 请求
       ↓
Grasp Core API (认证、路由)
       ↓
┌─────────────────────────────────────┐
│         GLG Adapter                  │
│  ┌─────────────────────────────────┐ │
│  │ 1. 检查缓存                      │ │
│  │ 2. 调用 GLG API                 │ │
│  │ 3. 错误处理与重试               │ │
│  │ 4. 降级决策                      │ │
│  │ 5. 结果缓存                      │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
       ↓ (GLG 可用)
GLG Pipeline API
       ↓
┌─────────────────────────────────────┐
│  Stage 1 → Stage 2 → Stage 3        │
│  Discovery → Extraction → Build    │
└─────────────────────────────────────┘
       ↓
知识图谱 + 查询结果
```

---

## 3. API 接口定义

### 3.1 GLG 现有接口（被集成）

GLG Pipeline 暴露以下 FastAPI 接口：

| 端点 | 方法 | 描述 | 耗时估算 |
|------|------|------|----------|
| `/health` | GET | 健康检查 | < 100ms |
| `/configure` | POST | 配置流水线 | < 500ms |
| `/discovery` | POST | 阶段一：领域发现 | 5-30 分钟 |
| `/extract` | POST | 阶段二：精确提取 | 10-60 分钟 |
| `/build` | POST | 阶段三：知识构建 | 5-20 分钟 |
| `/query` | POST | 知识查询 | 1-10 秒 |

### 3.2 Grasp Core API（对外统一入口）

```yaml
Grasp-Knowledge-V1:
  info:
    title: Grasp Knowledge API
    version: 1.0.0
    description: Nexus Grasp 统一知识接口
  
  paths:
    /grasp/knowledge/query:
      post:
        summary: 查询知识库
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  question:
                    type: string
                    description: 查询问题
                  mode:
                    type: string
                    enum: [local, global]
                    default: local
                  filters:
                    type: object
                    properties:
                      domain:
                        type: string
                      timeRange:
                        type: string
                      confidence:
                        type: number
        responses:
          200:
            description: 查询成功
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/KnowledgeResponse'
          503:
            description: GLG 服务降级
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/DegradedResponse'
    
    /grasp/knowledge/extract:
      post:
        summary: 触发知识提取
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  documentPaths:
                    type: array
                    items:
                      type: string
                  schema:
                    type: object
                  options:
                    type: object
                    properties:
                      async:
                        type: boolean
                        default: true
        responses:
          202:
            description: 任务已接受
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/TaskResponse'
    
    /grasp/knowledge/status/{taskId}:
      get:
        summary: 查询任务状态
        parameters:
          - name: taskId
            in: path
            required: true
            schema:
              type: string
        responses:
          200:
            description: 任务状态
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/TaskStatus'
    
    /grasp/knowledge/cancel/{taskId}:
      post:
        summary: 取消任务
        parameters:
          - name: taskId
            in: path
            required: true
            schema:
              type: string
        responses:
          200:
            description: 取消成功

  components:
    schemas:
      KnowledgeResponse:
        type: object
        properties:
          answer:
            type: string
          sources:
            type: array
            items:
              type: object
              properties:
                content:
                  type: string
                confidence:
                  type: number
                documentId:
                  type: string
          metadata:
            type: object
            properties:
              queryMode:
                type: string
              processingTimeMs:
                type: integer
              cacheHit:
                type: boolean

      DegradedResponse:
        type: object
        properties:
          status:
            type: string
            example: degraded
          message:
            type: string
          fallbackAnswer:
            type: string
          cachedResults:
            type: array
            items:
              type: object

      TaskResponse:
        type: object
        properties:
          taskId:
            type: string
          status:
            type: string
            enum: [pending, running, completed, failed, cancelled]
          estimatedCompletionTime:
            type: string
            format: date-time

      TaskStatus:
        type: object
        properties:
          taskId:
            type: string
          status:
            type: string
          progress:
            type: number
            minimum: 0
            maximum: 100
          currentStage:
            type: string
            enum: [discovery, extraction, build, query]
          error:
            type: string
```

### 3.3 GLG Adapter 接口（内部）

```python
# glg_adapter/interfaces.py

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio

class GLGHealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ExtractionRequest:
    document_paths: List[str]
    schema: Dict[str, Any]
    options: Dict[str, Any]
    callback_url: Optional[str] = None

@dataclass
class ExtractionResult:
    task_id: str
    status: StageStatus
    progress: float  # 0.0 - 1.0
    current_stage: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class QueryRequest:
    question: str
    mode: str = "local"  # local or global
    filters: Optional[Dict[str, Any]] = None

@dataclass
class QueryResult:
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    confidence: float
    cache_hit: bool

class IGLGAdapter(ABC):
    """GLG 适配器接口定义"""
    
    @abstractmethod
    async def health_check(self) -> GLGHealthStatus:
        """检查 GLG 服务健康状态"""
        pass
    
    @abstractmethod
    async def extract_knowledge(
        self, 
        request: ExtractionRequest
    ) -> ExtractionResult:
        """触发知识提取"""
        pass
    
    @abstractmethod
    async def query_knowledge(
        self, 
        request: QueryRequest
    ) -> QueryResult:
        """查询知识库"""
        pass
    
    @abstractmethod
    async def get_task_status(
        self, 
        task_id: str
    ) -> ExtractionResult:
        """获取任务状态"""
        pass
    
    @abstractmethod
    async def cancel_task(
        self, 
        task_id: str
    ) -> bool:
        """取消任务"""
        pass
```

---

## 4. 错误处理设计

### 4.1 错误分类

| 错误类别 | 错误码 | 描述 | 处理策略 |
|----------|--------|------|----------|
| `GLG_CONNECTION_ERROR` | 1001 | 无法连接到 GLG 服务 | 重试 → 降级 |
| `GLG_TIMEOUT_ERROR` | 1002 | GLG 请求超时 | 重试 → 降级 |
| `GLG_STAGE_ERROR` | 1003 | GLG 某个阶段失败 | 降级 |
| `GLG_RESOURCE_ERROR` | 1004 | GLG 资源不足 | 排队 → 降级 |
| `GLG_INVALID_REQUEST` | 1005 | 请求参数错误 | 返回错误 |
| `GLG_CANCELLED` | 1006 | 任务被取消 | 清理状态 |

### 4.2 错误处理流程

```
请求进入 GLG Adapter
       ↓
┌─────────────────────────────────────────┐
│         错误检测与分类                   │
└─────────────────────────────────────────┘
       ↓
┌──────────────┬──────────────────────────┐
│ 可重试错误   │    不可重试错误          │
│ (1001/1002) │    (1003/1004/1005/1006) │
└──────┬──────┴──────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  重试策略: Exponential Backoff          │
│  - 最大重试次数: 3                      │
│  - 初始间隔: 1s                         │
│  - 最大间隔: 30s                         │
│  - 抖动: ±20%                           │
└─────────────────────────────────────────┘
       ↓ (重试成功)
    返回结果
       ↓ (重试耗尽)
┌─────────────────────────────────────────┐
│         降级策略决策                      │
└─────────────────────────────────────────┘
```

### 4.3 重试实现

```python
# glg_adapter/retry.py

import asyncio
import random
from typing import TypeVar, Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    jitter: float = 0.2

class RetryableError(Exception):
    """可重试的错误"""
    pass

class NonRetryableError(Exception):
    """不可重试的错误"""
    pass

async def with_retry(
    func: Callable[..., T],
    config: RetryConfig = None,
    error_types: tuple = (RetryableError,)
) -> T:
    """
    带重试的函数执行
    
    Args:
        func: 要执行的异步函数
        config: 重试配置
        error_types: 可重试的错误类型
    
    Returns:
        函数执行结果
    
    Raises:
        NonRetryableError: 不可重试的错误
        Exception: 所有重试耗尽后的最终错误
    """
    config = config or RetryConfig()
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func()
        except error_types as e:
            last_error = e
            if attempt == config.max_attempts:
                logger.error(f"All {config.max_attempts} attempts failed: {e}")
                raise
            
            # 计算延迟（带抖动）
            delay = min(
                config.initial_delay * (2 ** (attempt - 1)),
                config.max_delay
            )
            jitter_range = delay * config.jitter
            delay = delay + random.uniform(-jitter_range, jitter_range)
            
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)
        except NonRetryableError:
            raise
        except Exception as e:
            # 非预期的错误不重试
            logger.error(f"Unexpected error (not retryable): {e}")
            raise
    
    raise last_error
```

### 4.4 错误响应格式

```python
# glg_adapter/errors.py

from dataclasses import dataclass
from typing import Optional, Any, Dict
import json

@dataclass
class GLGErrorResponse:
    """GLG 错误响应"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None  # 秒
    fallback_available: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "retryAfter": self.retry_after,
                "fallbackAvailable": self.fallback_available
            }
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

# 预定义错误
class GLGErrors:
    CONNECTION_ERROR = GLGErrorResponse(
        error_code="GLG_CONNECTION_ERROR",
        message="无法连接到 GLG 服务",
        retry_after=5,
        fallback_available=True
    )
    
    TIMEOUT_ERROR = GLGErrorResponse(
        error_code="GLG_TIMEOUT_ERROR",
        message="GLG 请求超时",
        retry_after=10,
        fallback_available=True
    )
    
    STAGE_ERROR = GLGErrorResponse(
        error_code="GLG_STAGE_ERROR",
        message="GLG 处理阶段失败",
        retry_after=None,
        fallback_available=True
    )
    
    RESOURCE_ERROR = GLGErrorResponse(
        error_code="GLG_RESOURCE_ERROR",
        message="GLG 资源不足",
        retry_after=60,
        fallback_available=True
    )
    
    INVALID_REQUEST = GLGErrorResponse(
        error_code="GLG_INVALID_REQUEST",
        message="请求参数错误",
        retry_after=None,
        fallback_available=False
    )
```

---

## 5. 降级策略设计

### 5.1 降级层次

```
┌─────────────────────────────────────────────────────────────────┐
│                        Level 0: 完整服务                         │
│  GLG 全部功能可用，知识查询 + 知识提取                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (GLG 部分不可用)
┌─────────────────────────────────────────────────────────────────┐
│                     Level 1: 查询降级                           │
│  GLG 查询可用，提取不可用                                        │
│  - 使用缓存的知识图谱回答查询                                     │
│  - 提取请求进入队列，等待恢复                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (GLG 不可用)
┌─────────────────────────────────────────────────────────────────┐
│                     Level 2: 最小化服务                          │
│  仅缓存可用                                                      │
│  - 返回缓存中最相关的知识                                        │
│  - 所有操作异步化，恢复后处理                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (完全不可用)
┌─────────────────────────────────────────────────────────────────┐
│                     Level 3: 服务降级                            │
│  返回友好错误 + 降级提示                                         │
│  - 不暴露内部错误细节                                             │
│  - 提供降级后的能力说明                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 降级决策逻辑

```python
# glg_adapter/degradation.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import time
import logging

logger = logging.getLogger(__name__)

class DegradationLevel(Enum):
    FULL = 0          # 完整服务
    QUERY_ONLY = 1    # 仅查询
    CACHED_ONLY = 2   # 仅缓存
    DEGRADED = 3      # 服务降级

@dataclass
class DegradationState:
    level: DegradationLevel
    reason: str
    since: float  # Unix timestamp
    last_attempt: Optional[float] = None
    consecutive_failures: int = 0

class DegradationManager:
    """降级状态管理器"""
    
    # 降级阈值配置
    HEALTHY_THRESHOLD = 3       # 连续成功次数 -> FULL
    QUERY_THRESHOLD = 2         # 连续失败次数 -> QUERY_ONLY
    CACHED_THRESHOLD = 3         # 连续失败次数 -> CACHED_ONLY
    FULL_DEGRADATION_THRESHOLD = 5  # 连续失败次数 -> DEGRADED
    
    # 恢复尝试间隔
    RECOVERY_CHECK_INTERVAL = 30  # 秒
    
    def __init__(self):
        self._state = DegradationState(
            level=DegradationLevel.FULL,
            reason="initial",
            since=time.time()
        )
        self._cache: Dict[str, Any] = {}
    
    @property
    def current_level(self) -> DegradationLevel:
        return self._state.level
    
    @property
    def is_healthy(self) -> bool:
        return self._state.level == DegradationLevel.FULL
    
    def should_attempt_glg(self) -> bool:
        """是否应该尝试调用 GLG"""
        if self._state.level == DegradationLevel.DEGRADED:
            # 检查是否应该尝试恢复
            if time.time() - self._state.last_attempt > self.RECOVERY_CHECK_INTERVAL:
                self._state.last_attempt = time.time()
                return True
            return False
        return True
    
    def record_success(self):
        """记录成功调用"""
        self._state.consecutive_failures = 0
        if self._state.level != DegradationLevel.FULL:
            logger.info("GLG service recovered, upgrading to FULL")
            self._state.level = DegradationLevel.FULL
            self._state.reason = "service_recovered"
    
    def record_failure(self, error_type: str):
        """记录失败调用"""
        self._state.consecutive_failures += 1
        self._state.last_attempt = time.time()
        
        old_level = self._state.level
        
        if self._state.consecutive_failures >= self.FULL_DEGRADATION_THRESHOLD:
            self._state.level = DegradationLevel.DEGRADED
            self._state.reason = f"consecutive_failures:{self._state.consecutive_failures}"
        elif self._state.consecutive_failures >= self.CACHED_THRESHOLD:
            self._state.level = DegradationLevel.CACHED_ONLY
            self._state.reason = f"consecutive_failures:{self._state.consecutive_failures}"
        elif self._state.consecutive_failures >= self.QUERY_THRESHOLD:
            self._state.level = DegradationLevel.QUERY_ONLY
            self._state.reason = f"consecutive_failures:{self._state.consecutive_failures}"
        
        if old_level != self._state.level:
            logger.warning(
                f"GLG degradation level changed: {old_level.name} -> {self._state.level.name}, "
                f"reason: {self._state.reason}"
            )
    
    def get_fallback_response(self, request: QueryRequest) -> QueryResult:
        """获取降级响应"""
        if self._state.level == DegradationLevel.CACHED_ONLY:
            # 返回缓存结果
            cached = self._get_cached_results(request.question)
            return QueryResult(
                answer=self._generate_cached_fallback_answer(cached),
                sources=cached,
                metadata={
                    "degraded": True,
                    "level": self._state.level.name,
                    "message": "GLG 服务降级，返回缓存结果"
                },
                confidence=0.5,  # 降低置信度
                cache_hit=True
            )
        
        # Level 3: 完全降级
        return QueryResult(
            answer="抱歉，知识库服务暂时不可用。请稍后再试或联系管理员。",
            sources=[],
            metadata={
                "degraded": True,
                "level": self._state.level.name,
                "message": "GLG 服务不可用"
            },
            confidence=0.0,
            cache_hit=False
        )
    
    def _get_cached_results(self, query: str) -> List[Dict[str, Any]]:
        """从缓存获取相关结果"""
        # 简单实现：使用包含查询关键词的缓存
        results = []
        query_lower = query.lower()
        for key, value in self._cache.items():
            if any(word in key.lower() for word in query_lower.split()):
                results.append(value)
        return results[:5]  # 最多返回 5 条
    
    def _generate_cached_fallback_answer(self, cached: List[Dict[str, Any]]) -> str:
        """基于缓存生成降级回答"""
        if not cached:
            return "抱歉，暂时无法提供答案。"
        
        return "基于缓存数据回答：" + " | ".join([
            f"参考: {r.get('content', '')[:100]}..."
            for r in cached[:3]
        ])
```

### 5.3 缓存策略

```python
# glg_adapter/cache.py

from typing import Optional, Dict, Any, List
import hashlib
import json
import time
from dataclasses import dataclass

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: Optional[float] = None

class KnowledgeCache:
    """知识库缓存"""
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,  # 1 hour
        query_cache_ttl: int = 300  # 5 minutes for query results
    ):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._query_cache_ttl = query_cache_ttl
    
    def _generate_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_query_result(
        self, 
        question: str, 
        mode: str = "local"
    ) -> Optional[QueryResult]:
        """获取查询结果缓存"""
        key = self._generate_key("query", question, mode)
        entry = self._cache.get(key)
        
        if entry and entry.expires_at > time.time():
            entry.access_count += 1
            entry.last_accessed = time.time()
            return entry.value
        
        return None
    
    def set_query_result(
        self,
        question: str,
        mode: str,
        result: QueryResult
    ):
        """设置查询结果缓存"""
        key = self._generate_key("query", question, mode)
        self._set(key, result, self._query_cache_ttl)
    
    def get_extraction_result(
        self,
        document_hash: str,
        schema_hash: str
    ) -> Optional[Dict[str, Any]]:
        """获取提取结果缓存"""
        key = self._generate_key("extract", document_hash, schema_hash)
        entry = self._cache.get(key)
        
        if entry and entry.expires_at > time.time():
            return entry.value
        
        return None
    
    def set_extraction_result(
        self,
        document_hash: str,
        schema_hash: str,
        result: Dict[str, Any]
    ):
        """设置提取结果缓存"""
        key = self._generate_key("extract", document_hash, schema_hash)
        self._set(key, result, self._default_ttl)
    
    def _set(self, key: str, value: Any, ttl: int):
        """设置缓存"""
        # 缓存满时清除最少使用的条目
        if len(self._cache) >= self._max_size:
            self._evict_lru()
        
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=time.time() + ttl
        )
    
    def _evict_lru(self):
        """清除最少使用的缓存条目"""
        if not self._cache:
            return
        
        # 找出访问次数最少且最旧的条目
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (
                self._cache[k].access_count,
                self._cache[k].last_accessed or 0
            )
        )
        del self._cache[lru_key]
    
    def invalidate(self, pattern: str = None):
        """清除缓存"""
        if pattern:
            keys_to_delete = [
                k for k in self._cache.keys() 
                if pattern in k
            ]
            for key in keys_to_delete:
                del self._cache[key]
        else:
            self._cache.clear()
```

---

## 6. 会话与任务管理

### 6.1 长时任务处理

GLG 的 discovery、extraction、build 阶段都是长时任务，需要：

1. **异步执行**: 立即返回 task_id
2. **状态跟踪**: 支持查询任务进度
3. **取消支持**: 支持取消正在执行的任务
4. **结果存储**: 完成后存储结果供后续查询

```python
# glg_adapter/task_manager.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import asyncio
import uuid
import time
import logging

logger = logging.getLogger(__name__)

class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    task_id: str
    task_type: str  # discovery, extraction, build
    state: TaskState
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0  # 0.0 - 1.0
    current_stage: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    callbacks: List[str] = field(default_factory=list)

class TaskManager:
    """任务管理器"""
    
    def __init__(self, max_concurrent: int = 3):
        self._tasks: Dict[str, Task] = {}
        self._max_concurrent = max_concurrent
        self._running_count = 0
        self._lock = asyncio.Lock()
    
    async def create_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        callback_url: Optional[str] = None
    ) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        
        async with self._lock:
            # 检查并发限制
            if self._running_count >= self._max_concurrent:
                raise RuntimeError(
                    f"Maximum concurrent tasks ({self._max_concurrent}) reached. "
                    "Please wait for existing tasks to complete."
                )
            
            self._tasks[task_id] = Task(
                task_id=task_id,
                task_type=task_type,
                state=TaskState.PENDING,
                created_at=time.time(),
                callbacks=[callback_url] if callback_url else []
            )
        
        # 启动任务执行
        asyncio.create_task(self._execute_task(task_id, task_type, params))
        
        return task_id
    
    async def _execute_task(
        self,
        task_id: str,
        task_type: str,
        params: Dict[str, Any]
    ):
        """执行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        async with self._lock:
            task.state = TaskState.RUNNING
            task.started_at = time.time()
            self._running_count += 1
        
        try:
            if task_type == "discovery":
                result = await self._run_discovery(task, params)
            elif task_type == "extraction":
                result = await self._run_extraction(task, params)
            elif task_type == "build":
                result = await self._run_build(task, params)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            async with self._lock:
                task.state = TaskState.COMPLETED
                task.completed_at = time.time()
                task.result = result
                task.progress = 1.0
            
            # 执行回调
            await self._execute_callbacks(task)
            
        except asyncio.CancelledError:
            async with self._lock:
                task.state = TaskState.CANCELLED
                task.completed_at = time.time()
            logger.info(f"Task {task_id} cancelled")
            
        except Exception as e:
            async with self._lock:
                task.state = TaskState.FAILED
                task.completed_at = time.time()
                task.error = str(e)
            logger.error(f"Task {task_id} failed: {e}")
            
        finally:
            async with self._lock:
                self._running_count -= 1
    
    async def _run_discovery(self, task: Task, params: Dict[str, Any]):
        """执行 discovery 任务"""
        # 实现调用 GLG discovery 的逻辑
        pass
    
    async def _run_extraction(self, task: Task, params: Dict[str, Any]):
        """执行 extraction 任务"""
        pass
    
    async def _run_build(self, task: Task, params: Dict[str, Any]):
        """执行 build 任务"""
        pass
    
    async def _execute_callbacks(self, task: Task):
        """执行回调通知"""
        for callback_url in task.callbacks:
            try:
                # 发送 HTTP POST 到回调 URL
                await self._send_callback(callback_url, task)
            except Exception as e:
                logger.error(f"Callback failed for task {task.task_id}: {e}")
    
    async def _send_callback(self, url: str, task: Task):
        """发送回调请求"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "taskId": task.task_id,
                "state": task.state.value,
                "result": task.result,
                "error": task.error
            }
            async with session.post(url, json=payload) as resp:
                if resp.status >= 400:
                    logger.warning(f"Callback returned status {resp.status}")
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return self._tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            return False
        
        # 任务会在下一次检查时被取消
        # 实际取消由执行循环处理
        return True
```

---

## 7. 可观测性设计

### 7.1 关键指标

| 指标名称 | 类型 | 描述 | 告警阈值 |
|----------|------|------|----------|
| `glg_request_total` | Counter | GLG 请求总数 | - |
| `glg_request_duration_seconds` | Histogram | 请求耗时分布 | P99 > 30s |
| `glg_error_total` | Counter | 错误总数（按类型） | > 10/min |
| `glg_cache_hit_ratio` | Gauge | 缓存命中率 | < 0.6 |
| `glg_degradation_level` | Gauge | 当前降级等级 | > 0 |
| `glg_active_tasks` | Gauge | 当前活跃任务数 | > max_concurrent |
| `glg_queue_size` | Gauge | 等待处理的任务数 | > 100 |

### 7.2 日志规范

```python
import structlog

logger = structlog.get_logger("glg_adapter")

# 标准日志格式
log = logger.bind(
    component="glg_adapter",
    version="1.0.0",
    trace_id="${TRACE_ID}",  # OpenTelemetry trace ID
    span_id="${SPAN_ID}"
)

# 日志事件
log.info("glg.request.started",
    request_type="query",
    question_length=len(question),
    mode=mode
)

log.info("glg.request.completed",
    request_type="query",
    duration_ms=duration,
    cache_hit=cache_hit,
    confidence=confidence
)

log.error("glg.request.failed",
    request_type="query",
    error_code="GLG_TIMEOUT_ERROR",
    attempt=attempt,
    max_attempts=3
)

log.warning("glg.degradation.triggered",
    old_level="FULL",
    new_level="QUERY_ONLY",
    reason="consecutive_failures:2"
)
```

### 7.3 健康检查

```python
# glg_adapter/health.py

from dataclasses import dataclass
from typing import Dict, Any, List
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    status: str  # healthy, degraded, unhealthy
    checks: Dict[str, Any]
    details: Dict[str, Any]

class HealthChecker:
    """健康检查器"""
    
    def __init__(self, glg_adapter, cache, degradation_manager):
        self._glg = glg_adapter
        self._cache = cache
        self._degradation = degradation_manager
    
    async def check(self) -> HealthStatus:
        """执行健康检查"""
        checks = {}
        details = {}
        
        # 1. GLG 连通性检查
        try:
            glg_health = await self._glg.health_check()
            checks["glg_connectivity"] = "pass"
            details["glg_status"] = glg_health.value
        except Exception as e:
            checks["glg_connectivity"] = "fail"
            details["glg_error"] = str(e)
        
        # 2. 缓存健康检查
        cache_size = len(self._cache._cache)
        checks["cache"] = "pass" if cache_size > 0 else "warn"
        details["cache_size"] = cache_size
        
        # 3. 降级状态检查
        degradation_level = self._degradation.current_level.value
        checks["degradation"] = "pass" if degradation_level == 0 else "degraded"
        details["degradation_level"] = degradation_level
        
        # 4. 任务队列检查
        active_tasks = len([t for t in self._glg._task_manager._tasks.values() 
                          if t.state == TaskState.RUNNING])
        checks["task_queue"] = "pass" if active_tasks < self._glg._task_manager._max_concurrent else "overloaded"
        details["active_tasks"] = active_tasks
        
        # 综合判断
        if any(v == "fail" for v in checks.values()):
            status = "unhealthy"
        elif any(v == "degraded" or v == "warn" for v in checks.values()):
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthStatus(
            status=status,
            checks=checks,
            details=details
        )
```

---

## 8. 部署与配置

### 8.1 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Nexus Platform                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Grasp Agent + Core API                    │  │
│  │                  (Kubernetes Pod)                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│                            │ HTTP                          │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                    GLG Service                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              GLG Pipeline + FastAPI                   │  │
│  │                  (独立 Pod/VM)                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 配置项

```yaml
# glg_adapter/config.yaml

glg:
  # GLG 服务地址
  base_url: "http://glg-service:8000"
  
  # 超时配置
  timeout:
    connect: 5    # 连接超时（秒）
    read: 30      # 读取超时（秒）
    total: 60     # 总超时（秒）
  
  # 重试配置
  retry:
    max_attempts: 3
    initial_delay: 1.0
    max_delay: 30.0
    jitter: 0.2

cache:
  # 缓存配置
  enabled: true
  max_size: 10000
  default_ttl: 3600      # 提取结果缓存（秒）
  query_cache_ttl: 300   # 查询结果缓存（秒）

degradation:
  # 降级配置
  healthy_threshold: 3
  query_threshold: 2
  cached_threshold: 3
  full_degradation_threshold: 5
  recovery_check_interval: 30

task:
  # 任务配置
  max_concurrent: 3
  default_timeout: 3600   # 任务默认超时（秒）

observability:
  # 可观测性配置
  metrics_enabled: true
  tracing_enabled: true
  log_level: "INFO"
```

### 8.3 环境变量覆盖

```bash
# GLG 服务地址
export GLG_BASE_URL="http://glg-service:8000"

# 超时配置
export GLG_TIMEOUT_CONNECT=5
export GLG_TIMEOUT_READ=30

# 缓存配置
export GLG_CACHE_ENABLED=true
export GLG_CACHE_MAX_SIZE=10000

# 日志级别
export GLG_LOG_LEVEL=INFO
```

---

## 9. 版本与变更

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-04-03 | 初始版本 | 麻子 |

---

## 10. 待明确事项

1. **缓存一致性**: 当 GLG 重新处理文档时，如何使缓存失效？
2. **多 GLG 实例**: 未来是否需要支持多个 GLG 实例的负载均衡？
3. **Schema 版本管理**: GLG 提取使用的 schema 版本如何管理？
4. **成本计量**: GLG 调用的成本如何计量和分摊？
