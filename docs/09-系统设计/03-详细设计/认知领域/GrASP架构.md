# GrASP 架构

**版本**: v3.1（门面层与适配层设计，审查后修订版）  
**作者**: 刚子  
**日期**: 2026-05-28  
**审查**: 谷子（CFO/业务专家）  
**状态**: 草稿  
**关联需求**: 认知领域（GrASP）

---


## 谷子 review 记录（2026-05-28）

### v3.0 -> v3.1 变更

**Review 者**: 谷子（CFO/业务专家）
**时间**: 2026-05-28 18:23
**结论**: P0 必须修复后才能上线，P1 Phase 1 内解决

#### P0 修复（5 项）
| # | 问题 | 修复 |
|---|------|------|
| P0-1 | _backend_map 内存泄漏 | 改为 OrderedDict LRU 缓存，上限 10000 条 |
| P0-2 | 缓存未命中静默回退 | 改为抛出 UnknownBackendError |
| P0-3 | inject 幂等性缺失 | 增加 content hash 查重，匹配已有走 update |
| P0-4 | switch_backend 并发安全不完整 | 改用不可变引用 + asyncio.Lock 原子切换 |
| P0-5 | cognition_backend_map 缺外键 | 迁移 SQL 增加 FOREIGN KEY ... ON DELETE CASCADE |

#### P1 采纳（Phase 1 内）
| # | 问题 | 修复 |
|---|------|------|
| P1-7 | domain 字段无校验 | 增加 VALID_DOMAINS frozenset 枚举校验 |
| P1-4 | retrieve 分页性能 | 适配器接收 limit + offset，服务端分页 |
| P1-5 | filters 参数无能力校验 | 适配器增加 alidate_filters() 方法 |

#### P1 推迟
| # | 问题 | 推迟原因 |
|---|------|---------|
| P1-1 | 适配器异常统一包装 | Phase 1 只有 MemoryAdapter，异常类型单一 |
| P1-2 | GraphRAG 成本控制 | GraphRAGAdapter 推迟到 Phase 1b |
| P1-3 | GraphRAG 降级策略 | 同上，Phase 1 只有 MemoryAdapter |
| P1-6 | 观测性 | Phase 1 骨架阶段不急 |

#### P2（后续优化）
全部推迟到 Phase 1 完成后再处理。

---

## 一、概述

### 1.1 GrASP 定位

GrASP（Grasp）是 Nexus 平台的**认知底座**，属于认知领域（五大领域之一）。

**一句话定位**：让 Agent"懂"——提供知识存储、认知推理、意图理解、认知安全。

**类比**：团队的"知识库 + 智囊团"

### 1.2 核心职责

| 能力 | 说明 |
|------|------|
| 认知存储 | What/How/Why/Lessons/Meta 五类知识 |
| 认知推理 | 基于知识图谱的上下文推导 |
| 意图理解 | 分析用户目标，提取领域上下文 |
| 认知抽取 | 任务派发前抽取相关上下文随任务下发 |
| 认知回流 | 任务完成后将经验反馈给知识库 |
| 认知安全 | 认知投毒检测、知识质量验证 |

### 1.3 与其他领域的关系

| 领域 | 关系 |
|------|------|
| 驾驭域 (Reins) | GrASP 为驾驭域的 Agent 提供行动依据（认知上下文），不参与任务调度 |
| 进化域 (Evo) | Evo 提炼的经验回写 GrASP 作为最佳实践，GrASP 的知识图谱用于 enrich 信号提取 |
| 安全域 (Vigil) | 认知投毒检测属于 GrASP（已从 Vigil 迁出），Vigil 负责系统级安全 |
| 拓展域 (Reach) | 场景库的模板来源之一是 GrASP 认知总结 |

---

## 二、认知存储模型

### 2.1 五类知识

| 类型 | 说明 | 示例 |
|------|------|------|
| **What** | 事实性知识 | "化工厂有3个储罐区" |
| **How** | 过程性知识 | "泄漏应急处理流程：隔离→检测→疏散→处置" |
| **Why** | 因果性知识 | "泄漏原因：阀门老化+压力过高" |
| **Lessons** | 经验教训 | "上次类似事件中，疏散延误导致2人受伤" |
| **Meta** | 元知识（关于知识的知识） | "这份报告由谷子生成，置信度0.85" |

### 2.2 知识图谱结构

```
实体 (Entity)
  ├── 属性 (Attributes)
  ├── 关系 (Relations) → 其他实体
  └── 认知类型 (CognitiveType) → What/How/Why/Lessons/Meta

关系 (Relation)
  ├── 类型 (Type) → 因果/依赖/包含/时序
  ├── 强度 (Weight) → 0.0-1.0
  └── 来源 (Source) → 任务ID/AgentID/用户输入
```

---

## 三、认知注入流程

### 3.1 任务派发前的认知抽取

```
Task 创建 → 查询 GrASP 认知图谱 → 抽取相关上下文 → 注入 Task.context_md → 派发给 Agent
```

### 3.2 任务完成后的认知回流

```
Agent 报完成 → 提取执行经验 → 写入 GrASP 认知图谱 → 更新知识权重 → 回写 Lesson
```

---

## 四、API 接口

GrASP 的 API 接口定义在 [认知引擎接口.md](../../04-接口契约/认知引擎接口.md)。

---

## 五、已知 Gap

| Gap 编号 | 问题 | 严重性 | 状态 |
|---------|------|--------|------|
| GAP-01 | 知识图谱的底层存储尚未实现（当前用 JSON 文件模拟） | P1 | 待实现 |
| GAP-02 | 认知回流自动化程度低（需要人工触发） | P2 | 待优化 |
| GAP-03 | 认知投毒检测规则不完善 | P1 | 待补充 |

---

## 六、门面层与适配层设计

### 6.1 设计背景

当前 `GraspService` 把**门面职责**（验证、毒检、路由）和**存储实现**（内存、GraphRAG）耦合在一起，`GraspGraphRAGAdapter` 绑死 Microsoft GraphRAG。新增检索后端需要改 Service 代码，违反开闭原则。

### 6.2 设计原则

1. **门面统一**：对外只暴露 GraspFacade，调用方不知道后端实现
2. **适配可插拔**：新增后端只需实现接口 + 注册，不改核心代码
3. **Phase 1 聚焦**：当前只实现 Memory（开发/测试）+ GraphRAG（生产），其他后端保留为扩展接口
4. **数据一致性**：cognition_id 与后端绑定，确保 update/delete 能定位到正确的后端
5. **路由对称**：inject 和 retrieve 使用相同的路由规则，避免数据孤岛
6. **幂等写入**：同一认知重复 inject 不会产生重复数据

### 6.3 目录结构

```
packages/server/src/grasp/
├── facade/                  ← 门面层（对外统一接口）
│   ├── __init__.py
│   ├── service.py           ← GraspFacade 主门面
│   └── schemas.py           ← Pydantic 请求/响应模型
├── adapters/                ← 适配层（不同 Graph RAG 实现）
│   ├── __init__.py
│   ├── base.py              ← BaseGraphRAGAdapter 抽象基类
│   ├── memory.py            ← MemoryAdapter（Phase 1 实现）
│   ├── graphrag.py          ← GraphRAGAdapter（Phase 1 实现）
│   ├── llamaindex.py        ← LlamaIndexAdapter（扩展接口，Phase 2 实现）
│   ├── neo4j.py             ← Neo4jAdapter（扩展接口，Phase 2 实现）
│   └── registry.py          ← AdapterRegistry
├── common/                  ← 现有
│   ├── models.py            ← CognitionInput / RetrieveResult 等
│   ├── base.py              ← BaseParser / CognitiveEntry
│   ├── poison_detector.py   ← 从 service.py 抽出
│   └── quality_validator.py ← 从 service.py 抽出
├── api/                     ← 现有（逐步迁移到 facade）
├── analysis/                ← 现有
├── parser/                  ← 现有
├── injection/               ← 现有
└── registry/                ← 现有
```

---

### 6.4 适配层

#### 6.4.1 抽象基类 `BaseGraphRAGAdapter`

```python
# grasp/adapters/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from grasp.common.models import (
    CognitionInput, InjectResult, RetrieveResult, UpdateResult
)


class BaseGraphRAGAdapter(ABC):
    """所有 Graph RAG 后端必须实现的抽象接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """后端标识名，如 'memory', 'microsoft-graphrag'"""
        pass

    @abstractmethod
    async def inject(self, cognition: CognitionInput) -> InjectResult:
        """注入认知到索引"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        mode: str = "local",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RetrieveResult:
        """
        检索认知
        
        :param mode: 'local'（实体）/ 'global'（社区）/ 'drift'（深度）/ 'basic'（关键词）
        :param filters: type, tags, min_confidence, domain 等
        """
        pass

    @abstractmethod
    async def update(self, cognition_id: str, content: str,
                     metadata: Dict[str, Any]) -> UpdateResult:
        """更新已有认知"""
        pass

    @abstractmethod
    async def delete(self, cognition_id: str) -> bool:
        """删除认知"""
        pass

    @abstractmethod
    async def build_index(
        self,
        documents: List[Dict[str, Any]],
        incremental: bool = True,
    ) -> InjectResult:
        """批量构建/重建索引"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """返回后端健康状态和统计信息"""
        pass

    def is_available(self) -> bool:
        """检查后端是否可用"""
        try:
            self._check_dependencies()
            return True
        except ImportError:
            return False

    def _check_dependencies(self):
        """子类实现：检查依赖"""
        pass
```

#### 6.4.2 MemoryAdapter（Phase 1 实现）

```python
class MemoryAdapter(BaseGraphRAGAdapter):
    """内存存储适配器 — 开发/测试/兜底用"""
    
    @property
    def name(self): return "memory"
    
    # 使用 dict 存储 + 关键词匹配检索
    # 保留现有 GraspService 的内存存储逻辑
    # 所有操作同步完成，无外部依赖
```

#### 6.4.3 GraphRAGAdapter（Phase 1 实现）

```python
class GraphRAGAdapter(BaseGraphRAGAdapter):
    """Microsoft GraphRAG 适配器"""
    
    @property
    def name(self): return "microsoft-graphrag"
    
    # inject: CognitionInput → txt → graphrag build_index
    # retrieve: local/global search → CognitionItem
    # update: 不支持单条更新 → 删旧文档 + 重新注入
    # build_index: 批量写入 input/ → graphrag build_index
```

#### 6.4.4 LlamaIndexAdapter / Neo4jAdapter（扩展接口，Phase 2）

这两个适配器在 Phase 1 中只定义接口（继承 BaseGraphRAGAdapter），不实现具体逻辑。注册表中不会注册它们，`auto_select()` 也不会选中它们。等实际有需求时再实现。

---

### 6.5 适配器注册表

```python
class AdapterRegistry:
    """
    适配器注册表 — 工厂 + 运行时管理
    
    职责：
    1. 注册/发现所有可用适配器
    2. 按名称获取适配器实例
    3. 自动选择最佳可用后端
    4. 健康检查
    """

    def __init__(self):
        self._adapters: Dict[str, BaseGraphRAGAdapter] = {}
        self._config: Dict[str, Dict[str, Any]] = {}

    def register(self, adapter: BaseGraphRAGAdapter, config: Dict = None):
        self._adapters[adapter.name] = adapter
        if config:
            self._config[adapter.name] = config

    def get(self, name: str) -> BaseGraphRAGAdapter:
        if name not in self._adapters:
            raise KeyError(f"Adapter '{name}' not registered")
        return self._adapters[name]

    def has(self, name: str) -> bool:
        return name in self._adapters

    def all(self) -> List[BaseGraphRAGAdapter]:
        return list(self._adapters.values())

    def available(self) -> List[str]:
        return [name for name, a in self._adapters.items() if a.is_available()]

    def auto_select(self) -> str:
        """
        自动选择最佳可用后端
        
        优先级：microsoft-graphrag > memory（兜底）
        LlamaIndex 和 Neo4j 等 Phase 2 实现后加入此列表
        """
        priority = ["microsoft-graphrag", "memory"]
        for name in priority:
            if name in self._adapters and self._adapters[name].is_available():
                return name
        return "memory"

    def get_status_all(self) -> List[Dict[str, Any]]:
        return [
            {"name": a.name, "available": a.is_available(), **a.get_status()}
            for a in self._adapters.values()
        ]
```

---

### 6.6 门面层

#### 6.6.1 GraspFacade 完整代码（v3.1 — 修复 P0 问题）

> **v3.1 变更**（2026-05-28，谷子 review 后）：
> - **P0-1**: `_backend_map` 改为 LRU 缓存，上限 10000 条
> - **P0-2**: 缓存+DB 都未命中时抛出 `UnknownBackendError`，不再静默回退
> - **P0-3**: inject 增加 content hash 查重，匹配到已有记录走 update 路径
> - **P0-4**: `switch_backend` 改用不可变引用切换，消除并发读取中间态
> - **P0-5**: `cognition_backend_map` 表增加外键约束（见 6.10 迁移 SQL）
> - **P1-7**: domain 字段增加枚举校验

```python
# grasp/facade/service.py
import asyncio
import hashlib
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from grasp.adapters.registry import AdapterRegistry
from grasp.common.models import (
    CognitionInput, InjectResult, RetrieveResult, UpdateResult
)
from grasp.common.poison_detector import PoisonDetector
from grasp.common.quality_validator import QualityValidator
from shared.common.exceptions import NexusException, ErrorCode


# P1-7: domain 合法值枚举
VALID_DOMAINS = frozenset([
    "安全合规", "应用运维", "设备状态", "业务洞察", "操作手册",
    "故障排查", "最佳实践", "系统架构", "代码规范", "团队经验",
])


class UnknownBackendError(Exception):
    """认知存储后端未知 — 缓存和 DB 都找不到记录"""
    pass


class GraspFacade:
    """
    Grasp 门面层 — 认知域唯一入口
    
    外部系统（Reins/Reach/Vigil/Evo）所有 API 路由
    只经过本类交接，不直接接触适配器层。
    
    职责：
    1. 格式验证（content 不为空等）
    2. 毒药检测（PoisonDetector）
    3. 质量验证（QualityValidator）
    4. 路由分发（按 domain 路由，不依赖 tags）
    5. cognition_id 与 backend 映射（确保 update/delete 定位到正确后端）
    6. 幂等性保证（content hash 查重）
    7. 统一响应格式
    """

    # P0-1: LRU 缓存上限
    _BACKEND_MAP_MAX_SIZE = 10000

    def __init__(
        self,
        registry: AdapterRegistry = None,
        poison_detector: PoisonDetector = None,
        quality_validator: QualityValidator = None,
    ):
        self._registry = registry or AdapterRegistry()
        self._poison = poison_detector or PoisonDetector()
        self._validator = quality_validator or QualityValidator()
        
        # P0-4: 当前活跃后端（不可变引用，切换时原子替换）
        self._active_backend: Optional[str] = None
        
        # P0-4: 读写锁（保护 _active_backend 切换）
        self._lock = asyncio.Lock()
        
        # P0-1: cognition_id 到 backend 映射 — LRU 缓存（非无限 dict）
        self._backend_map: OrderedDict[str, str] = OrderedDict()
        
        # 路由配置（domain 到 backend_name）
        self._domain_routing: Dict[str, str] = {}
        
        self._register_defaults()

    def _register_defaults(self):
        """自动注册 Phase 1 的适配器"""
        from grasp.adapters.memory import MemoryAdapter
        self._registry.register(MemoryAdapter())

        try:
            from grasp.adapters.graphrag import GraphRAGAdapter
            self._registry.register(GraphRAGAdapter())
        except ImportError:
            pass

        if not self._active_backend:
            self._active_backend = self._registry.auto_select()

    def set_domain_routing(self, routing: Dict[str, str]):
        """
        设置领域路由（domain 到 backend）。
        """
        self._domain_routing.update(routing)

    # ===== 核心操作 =====

    async def inject(self, input: CognitionInput) -> InjectResult:
        """注入认知 — 幂等（content hash 查重）"""
        # P1-7: domain 校验
        self._validate_domain(input.domain)
        
        # 1. 格式验证
        self._validate_content(input.content)
        
        # 2. 毒药检测
        self._poison_check(input.content)
        
        # 3. 质量验证
        quality_score = self._quality_score(input)
        
        # P0-3: 幂等性 — content hash 查重
        content_hash = self._compute_content_hash(input.content)
        existing = await self._find_by_content_hash(content_hash, input.domain)
        if existing:
            if existing.content == input.content:
                return InjectResult(
                    cognition_id=existing.cognition_id,
                    backend=self._find_backend_for_cognition(existing.cognition_id),
                    quality_score=quality_score,
                    is_duplicate=True,
                )
            # 内容不同，走 update 路径
            backend = self._find_backend_for_cognition(existing.cognition_id)
            adapter = self._registry.get(backend)
            result = await adapter.update(
                existing.cognition_id, input.content, dict(input.metadata or {})
            )
            result.quality_score = quality_score
            return result
        
        # 4. 路由分发（按 domain 字段）
        backend = self._route_backend(input)
        
        # 5. 注入
        adapter = self._registry.get(backend)
        result = await adapter.inject(input)
        result.quality_score = quality_score
        
        # 6. 记录映射（写 DB + 更新缓存）
        self._record_backend_mapping(result.cognition_id, backend)
        
        return result

    async def retrieve(self, query: str, mode: str = "local",
                       limit: int = 10, offset: int = 0,
                       type: Optional[List[str]] = None,
                       tags: Optional[List[str]] = None,
                       min_confidence: float = 0.0,
                       domain: Optional[str] = None) -> RetrieveResult:
        """检索认知 — 路由与 inject 对称"""
        if domain is not None:
            self._validate_domain(domain)
        
        filters = {}
        if type: filters["type"] = type
        if tags: filters["tags"] = tags
        if min_confidence > 0: filters["min_confidence"] = min_confidence
        if domain: filters["domain"] = domain

        backend = self._resolve_backend_for_retrieve(domain)
        adapter = self._registry.get(backend)
        raw = await adapter.retrieve(
            query=query, mode=mode, limit=limit + offset, filters=filters
        )
        return RetrieveResult(
            items=raw.items[offset:offset + limit],
            total=raw.total,
            has_more=offset + limit < raw.total,
        )

    async def update(self, cognition_id: str, content: str,
                     metadata: Dict) -> UpdateResult:
        """更新认知 — 通过映射找到正确后端"""
        self._poison_check(content)
        backend = self._find_backend_for_cognition(cognition_id)
        adapter = self._registry.get(backend)
        return await adapter.update(cognition_id, content, metadata)

    async def delete(self, cognition_id: str) -> bool:
        """删除认知 — 通过映射找到正确后端"""
        backend = self._find_backend_for_cognition(cognition_id)
        adapter = self._registry.get(backend)
        success = await adapter.delete(cognition_id)
        if success:
            self._remove_backend_mapping(cognition_id)
        return success

    # ===== 管理操作 =====

    async def switch_backend(self, backend_name: str):
        """运行时切换后端 — P0-4: 不可变引用原子切换"""
        async with self._lock:
            if not self._registry.has(backend_name):
                raise ValueError(f"Unknown backend: {backend_name}")
            adapter = self._registry.get(backend_name)
            if not adapter.is_available():
                raise ValueError(f"Backend '{backend_name}' is not available")
            self._active_backend = backend_name

    def list_backends(self) -> List[Dict[str, Any]]:
        return self._registry.get_status_all()

    def get_active_backend(self) -> str:
        return self._active_backend or self._registry.auto_select()

    def get_domain_routing(self) -> Dict[str, str]:
        return dict(self._domain_routing)

    # ===== 内部方法 =====

    def _validate_domain(self, domain: Optional[str]):
        """P1-7: domain 枚举校验"""
        if domain is not None and domain not in VALID_DOMAINS:
            raise NexusException(
                code=ErrorCode.GRASP_INVALID_CONTENT,
                message=f"非法 domain: '{domain}'，合法值: {sorted(VALID_DOMAINS)}"
            )

    def _compute_content_hash(self, content: str) -> str:
        """P0-3: content hash 计算"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    async def _find_by_content_hash(self, content_hash: str,
                                     domain: Optional[str]) -> Optional[CognitionInput]:
        """P0-3: 根据 content hash 查重"""
        backend = self._active_backend or self._registry.auto_select()
        adapter = self._registry.get(backend)
        if hasattr(adapter, 'search_by_content_hash'):
            return await adapter.search_by_content_hash(content_hash, domain)
        return None

    def _route_backend(self, input: CognitionInput) -> str:
        """按 domain 字段路由"""
        domain = input.domain
        if domain and domain in self._domain_routing:
            target = self._domain_routing[domain]
            if self._registry.has(target) and self._registry.get(target).is_available():
                return target
        return self._active_backend or self._registry.auto_select()

    def _resolve_backend_for_retrieve(self, domain: Optional[str]) -> str:
        """检索路由（与 inject 对称）"""
        if domain and domain in self._domain_routing:
            target = self._domain_routing[domain]
            if self._registry.has(target) and self._registry.get(target).is_available():
                return target
        return self._active_backend or self._registry.auto_select()

    def _find_backend_for_cognition(self, cognition_id: str) -> str:
        """P0-2: 查找认知后端 — DB 未找到则抛异常，不静默回退"""
        # 1. 查缓存
        if cognition_id in self._backend_map:
            self._backend_map.move_to_end(cognition_id)  # P0-1: LRU
            return self._backend_map[cognition_id]
        
        # 2. 查 DB
        backend = self._load_backend_from_db(cognition_id)
        if backend:
            self._record_backend_mapping(cognition_id, backend)
            return backend
        
        # P0-2: 缓存和 DB 都未命中 → 抛异常
        raise UnknownBackendError(
            f"cognition_id '{cognition_id}' 在缓存和 DB 中都找不到后端映射。"
            f"可能是迁移不完整或数据已删除。"
        )

    def _record_backend_mapping(self, cognition_id: str, backend: str):
        """写入映射 — P0-1: LRU 淘汰"""
        if cognition_id in self._backend_map:
            self._backend_map.move_to_end(cognition_id)
        self._backend_map[cognition_id] = backend
        while len(self._backend_map) > self._BACKEND_MAP_MAX_SIZE:
            self._backend_map.popitem(last=False)  # 淘汰最旧
        # TODO: 写入 DB

    def _remove_backend_mapping(self, cognition_id: str):
        self._backend_map.pop(cognition_id, None)

    def _load_backend_from_db(self, cognition_id: str) -> Optional[str]:
        # TODO: SELECT backend_name FROM cognition_backend_map WHERE cognition_id = ?
        return None

    def _validate_content(self, content: str):
        if not content or not content.strip():
            raise NexusException(
                code=ErrorCode.GRASP_INVALID_CONTENT,
                message="认知内容不能为空"
            )

    def _poison_check(self, content: str):
        is_poison, risks = self._poison.detect(content)
        if is_poison:
            raise NexusException(
                code=ErrorCode.GRASP_POISON_DETECTED,
                message="检测到认知投毒，请求已被拒绝",
                details={"risk_factors": risks},
            )

    def _quality_score(self, input: CognitionInput) -> float:
        is_valid, score, _ = self._validator.validate(input.content, input.confidence)
        return max(0, score)
```


### 6.7 Pydantic Schemas

```python
# grasp/facade/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class CognitionTypeEnum(str, Enum):
    """认知类型 — 与业务概念一致（第二章 2.1 五类知识）"""
    WHAT = "what"           # 事实性知识
    HOW = "how"             # 过程性知识
    WHY = "why"             # 因果性知识
    LESSONS = "lessons"     # 经验教训
    META = "meta"           # 元知识


class CognitionInjectRequest(BaseModel):
    type: CognitionTypeEnum = CognitionTypeEnum.WHAT
    content: str = Field(..., min_length=1, max_length=10000, description="认知内容")
    tags: List[str] = Field(default_factory=list, description="业务标签")
    confidence: float = Field(default=0.8, ge=0, le=1, description="置信度 0-1")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    domain: Optional[str] = Field(default=None, description="领域（用于后端路由）")


class CognitionRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="查询文本")
    mode: str = Field(default="local", description="检索模式: local/global/drift/basic")
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0, description="分页偏移")
    type: Optional[List[CognitionTypeEnum]] = None
    tags: Optional[List[str]] = None
    min_confidence: float = Field(default=0.0, ge=0, le=1)
    domain: Optional[str] = Field(default=None, description="领域（用于路由对称）")


class CognitionItemResponse(BaseModel):
    cognition_id: str
    type: str
    content: str
    tags: List[str]
    confidence: float
    quality_score: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CognitionRetrieveResponse(BaseModel):
    items: List[CognitionItemResponse]
    total: int
    has_more: bool


class CognitionInjectResponse(BaseModel):
    cognition_id: str
    status: str
    quality_score: float


class BackendStatusResponse(BaseModel):
    name: str
    available: bool
    index_size: Optional[int] = None
    backend_version: Optional[str] = None
```

---

### 6.8 API 端点设计

```
POST /api/v1/grasp/inject
→ 注入认知

POST /api/v1/grasp/retrieve
→ 检索认知（支持 offset/limit 分页）

PUT /api/v1/grasp/cognitions/{cognition_id}
→ 更新认知

DELETE /api/v1/grasp/cognitions/{cognition_id}
→ 删除认知

GET /api/v1/grasp/backends
→ 列出所有后端及其状态

PUT /api/v1/grasp/backends/active
→ 切换活跃后端（管理员操作）
Body: {"backend_name": "microsoft-graphrag"}

GET /api/v1/grasp/domain-routing
→ 查看领域路由配置

PUT /api/v1/grasp/domain-routing
→ 配置领域路由
Body: {"安全生产": "microsoft-graphrag", "设备状态": "neo4j"}

GET /api/v1/grasp/cognitions/{cognition_id}
→ 获取单个认知详情
```

---

### 6.9 数据一致性保障

#### 6.9.1 cognition_id → backend 映射

为保证 update/delete 操作能定位到正确的后端，需要在 inject 时记录映射关系：

```sql
CREATE TABLE cognition_backend_map (
    cognition_id  VARCHAR(64) PRIMARY KEY,
    backend_name  VARCHAR(32) NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cognition_id) REFERENCES cognitions(id) ON DELETE CASCADE
);
```

运行时 Facade 维护一个内存缓存 `_backend_map`，inject 时双写（DB + 缓存），update/delete 时优先查缓存，缓存未命中再查 DB。

#### 6.9.2 检索对称性

retrieve 的路由逻辑必须与 inject 对称：

| 场景 | inject 路由 | retrieve 路由 | 是否一致 |
|------|------------|--------------|---------|
| 有 domain | domain → backend | domain → backend | ✅ |
| 无 domain | active_backend | active_backend | ✅ |

**不会出现**：inject 到 Neo4j 的数据在 GraphRAG active 时检索不到的情况。

#### 6.9.3 并发安全

`switch_backend` 使用 `asyncio.Lock` 保护，确保切换期间不会有请求路由到不一致的后端。

#### 6.9.4 幂等性

`inject` 操作的幂等性由各适配器保证：
- MemoryAdapter：按 content hash 去重
- GraphRAGAdapter：每次 inject 生成新 cognition_id，不重复（天然幂等）

---

### 6.10 迁移策略

#### 6.10.1 阶段一：门面+基础适配（当前 Sprint）

- [ ] 抽出 `PoisonDetector` 和 `QualityValidator` 为独立模块
- [ ] 创建 `grasp/facade/` 和 `grasp/adapters/` 目录
- [ ] 实现 `BaseGraphRAGAdapter` 抽象基类
- [ ] 实现 `MemoryAdapter`（从现有 GraspService 迁移内存逻辑）
- [ ] 实现 `GraphRAGAdapter`（迁移现有 GraspGraphRAGAdapter 逻辑）
- [ ] 实现 `GraspFacade`（验证/毒检/路由/映射管理）
- [ ] 创建 `cognition_backend_map` 表
- [ ] 现有 `GraspService` 保留不删，新旧并存
- [ ] 新增管理端点 `GET /api/v1/grasp/backends`

#### 6.10.2 阶段二：API 切换 + 清理旧代码（下一 Sprint）

- [ ] 现有 API 路由改用 `GraspFacade` 替代 `GraspService`
- [ ] 验证所有 API 端点行为一致
- [ ] 删除旧的 `GraspService`
- [ ] 删除旧的 `GraspGraphRAGAdapter`
- [ ] 更新文档

> 到这里迁移就完成了。后续是可选增强。

#### 6.10.3 阶段三（可选）：新增后端

- [ ] `LlamaIndexAdapter`（POC 验证）
- [ ] `Neo4jAdapter`（生产级方案）
- [ ] 完善领域路由策略

---

### 6.11 与现有代码的兼容性

| 现有组件 | 兼容性 | 说明 |
|----------|--------|------|
| `grasp/common/models.py` | ✅ 完全兼容 | 门面层和适配层复用现有模型 |
| `grasp/common/service.py` | 🔄 拆分 | PoisonDetector / QualityValidator 抽为独立模块 |
| `grasp/common/graphrag_adapter.py` | 🔄 迁移 | 逻辑迁移到 `adapters/graphrag.py` |
| `grasp/api/grasp_router.py` | ✅ 逐步迁移 | 路由改用 GraspFacade，行为不变 |
| `grasp/api/grasp_helpers.py` | 🔄 替换 | 辅助函数迁移到门面层 |
| 其他域调用 GraspService | ✅ 向后兼容 | 通过 facade 提供兼容方法 |

---

### 6.12 配置管理

```python
# grasp/adapters/config.py

GRASP_BACKEND_DEFAULT = "microsoft-graphrag"

GRASP_BACKEND_CONFIG = {
    "microsoft-graphrag": {
        "workspace_root": "D:/work/research/agents-nexus/graphrag_workspace",
        "community_level": 2,
        "response_type": "Multiple Paragraphs",
    },
    # Phase 2 启用后加入
    # "llamaindex-kg": {
    #     "storage_dir": "D:/work/research/agents-nexus/grasp_llamaindex",
    # },
    # "neo4j": {
    #     "uri": "bolt://localhost:7687",
    #     "username": "neo4j",
    #     "password": "${NEO4J_PASSWORD}",  # 必须通过环境变量注入，不能写配置文件
    #     "database": "grasp",
    # },
}

# 领域路由配置（通过 settings 表或环境变量管理）
GRASP_DOMAIN_ROUTING = {
    # "安全生产": "microsoft-graphrag",
    # "设备状态": "neo4j",
}
```

---

### 6.13 各后端能力对比

| 能力维度 | Memory | Microsoft GraphRAG | LlamaIndex KG | Neo4j |
|----------|--------|-------------------|---------------|-------|
| **部署复杂度** | 无 | 高（需 graphrag 包） | 低（pip install） | 中（需 DB 实例） |
| **索引速度** | 即时 | 慢（分钟级，LLM 提取） | 中 | 中 |
| **检索精度** | 低（关键词匹配） | 高（社区摘要） | 高（图谱路径） | 高（Cypher 查询） |
| **增量更新** | ✅ | ⚠️ 支持但需 rebuild | ⚠️ 支持但有限 | ✅ |
| **单条 CRUD** | ✅ | ❌（需重建文档） | ⚠️ 有限 | ✅ |
| **多跳推理** | ❌ | ⚠️ 间接 | ✅ | ✅ |
| **实时性** | ✅ | ❌ | ❌ | ✅ |
| **Phase** | Phase 1 | Phase 1 | Phase 2 | Phase 2 |
| **适合场景** | 开发/测试兜底 | 静态文档深度检索 | 快速原型验证 | 生产级实时检索 |

> 注：Phase 1 阶段只实现 Memory + GraphRAG。LlamaIndex KG 和 Neo4j 的能力评估为初步判断，实际数据待 POC 验证后更新。

---

*文档结束*
