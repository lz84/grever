"""GraspFacade — Grasp 门面层（v3.2 — 统一异常包装）"""

import asyncio
import hashlib
import logging
from pathlib import Path
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from grasp.adapters.registry import AdapterRegistry
from grasp.facade.models import (
    CognitionInput, InjectResult, RetrieveResult, UpdateResult
)
from grasp.common.poison_detector import PoisonDetector
from grasp.common.quality_validator import QualityValidator
from shared.common.exceptions import NexusException, ErrorCode

logger = logging.getLogger(__name__)


# P1-7: domain 合法值枚举
VALID_DOMAINS = frozenset([
    "安全合规", "应用运维", "设备状态", "业务洞察", "操作手册",
    "故障排查", "最佳实践", "系统架构", "代码规范", "团队经验",
])


class UnknownBackendError(NexusException):
    """认知存储后端未知 — 缓存和 DB 都找不到记录"""

    def __init__(self, cognition_id: str):
        super().__init__(
            code=ErrorCode.GRASP_BACKEND_UNAVAILABLE,
            message=f"cognition_id '{cognition_id}' 在缓存和 DB 中都找不到后端映射。"
                    f"可能是迁移不完整或数据已删除。",
            details={"cognition_id": cognition_id},
        )


# ============================================================
# 异常包装常量
# ============================================================

_ADAPTER_ERROR_CODES = {
    "inject": ErrorCode.GRASP_INJECT_ERROR,
    "retrieve": ErrorCode.GRASP_RETRIEVE_ERROR,
    "update": ErrorCode.GRASP_UPDATE_ERROR,
    "delete": ErrorCode.GRASP_DELETE_ERROR,
}

# 适配器可能抛出的内部异常类型 — 需要被包装
_ADAPTER_INTERNAL_EXCEPTIONS = (
    RuntimeError,    # GraphRAGAdapter: 成本上限、CLI 错误
    KeyError,        # MemoryAdapter/GraphRAGAdapter: 认知不存在
    FileNotFoundError,
    OSError,
    IOError,
    PermissionError,
)


def _wrap_adapter_error(operation: str, exc: Exception) -> NexusException:
    """
    将适配器内部异常统一包装为 NexusException。

    - 不泄露适配器内部异常类型名、traceback 等细节
    - 根据操作类型分配对应的 ErrorCode
    - 保留 reference_id 供排查使用
    """
    code = _ADAPTER_ERROR_CODES.get(operation, ErrorCode.GRASP_STORAGE_ERROR)

    # KeyError → 认知不存在（更有语义的错误码）
    if isinstance(exc, KeyError):
        key = str(exc).strip("'\"")
        return NexusException(
            code=ErrorCode.GRASP_NOT_FOUND,
            message=f"认知 '{key}' 不存在",
            details={"cognition_id": key},
        )

    # RuntimeError → 后端不可用或配置问题
    if isinstance(exc, RuntimeError):
        return NexusException(
            code=ErrorCode.GRASP_BACKEND_UNAVAILABLE,
            message=str(exc),
            details={"operation": operation},
        )

    # 其他内部异常 → 按操作类型分配错误码
    return NexusException(
        code=code,
        message=f"认知后端执行 {operation} 时发生内部错误",
        details={"operation": operation},
    )


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
    8. 统一异常包装（适配器异常 → NexusException）
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

        # DB 引擎（懒加载）
        self._db_engine: Optional[Engine] = None

        # 路由配置（domain 到 backend_name）
        self._domain_routing: Dict[str, str] = {}

        self._register_defaults()

    def _register_defaults(self):
        """自动注册 Phase 1 的适配器"""
        from grasp.adapters.memory import MemoryAdapter
        self._registry.register(MemoryAdapter())

        try:
            from grasp.adapters.graphrag import GraphRAGAdapter
            self._graphrag_adapter = GraphRAGAdapter()
            self._registry.register(self._graphrag_adapter)

            # 注入 Facade 引用（用于降级回调）
            self._graphrag_adapter.set_facade(self)

            # 设置降级回调：GraphRAG 不可用时自动切换到 memory
            async def graphrag_fallback_handler(available: bool):
                if not available:
                    logger.warning("[GraspFacade] GraphRAG 不可用，自动降级到 memory")
                    async with self._lock:
                        if self._active_backend == "microsoft-graphrag":
                            self._active_backend = "memory"
                            logger.warning("[GraspFacade] 已切换到 memory 后端")
                else:
                    logger.info("[GraspFacade] GraphRAG 恢复，尝试切回")
                    async with self._lock:
                        if self._active_backend == "memory":
                            self._active_backend = "microsoft-graphrag"
                            logger.info("[GraspFacade] 已切换到 microsoft-graphrag 后端")

            self._graphrag_adapter.health_checker.set_fallback_handler(
                graphrag_fallback_handler
            )

        except ImportError:
            self._graphrag_adapter = None

        if not self._active_backend:
            self._active_backend = self._registry.auto_select()

    async def start_health_checker(self):
        """启动 GraphRAG 健康检查循环（仅当 GraphRAGAdapter 已注册时）"""
        if hasattr(self, '_graphrag_adapter') and self._graphrag_adapter is not None:
            await self._graphrag_adapter.health_checker.start()

    async def stop_health_checker(self):
        """停止 GraphRAG 健康检查循环"""
        if hasattr(self, '_graphrag_adapter') and self._graphrag_adapter is not None:
            await self._graphrag_adapter.health_checker.stop()

    def set_domain_routing(self, routing: Dict[str, str]):
        """设置领域路由（domain 到 backend）"""
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
        try:
            existing = await self._find_by_content_hash(content_hash, input.domain)
        except _ADAPTER_INTERNAL_EXCEPTIONS as e:
            # 查重失败不影响主流程，记录日志后继续
            logger.warning(f"[GraspFacade] content hash 查重失败: {e}")
            existing = None
        except NexusException:
            raise
        except Exception as e:
            logger.warning(f"[GraspFacade] content hash 查重异常: {e}")
            existing = None

        if existing:
            if existing.content == input.content:
                return InjectResult(
                    cognition_id=getattr(existing, 'cognition_id', ''),
                    backend=self._find_backend_for_cognition(
                        getattr(existing, 'cognition_id', '')
                    ),
                    quality_score=quality_score,
                    is_duplicate=True,
                )
            # 内容不同，走 update 路径
            cid = getattr(existing, 'cognition_id', '')
            backend = self._find_backend_for_cognition(cid)
            try:
                adapter = self._registry.get(backend)
                result = await adapter.update(
                    cid, input.content, dict(input.metadata or {})
                )
                result.quality_score = quality_score
                return result
            except _ADAPTER_INTERNAL_EXCEPTIONS as e:
                raise _wrap_adapter_error("update", e)

        # 4. 路由分发（按 domain 字段）
        backend = self._route_backend(input)

        # 5. 注入
        try:
            adapter = self._registry.get(backend)
            result = await adapter.inject(input)
            result.quality_score = quality_score
        except _ADAPTER_INTERNAL_EXCEPTIONS as e:
            raise _wrap_adapter_error("inject", e)

        # 6. 记录映射（写 DB + 更新缓存）
        self._record_backend_mapping(result.cognition_id, backend)

        return result

    async def retrieve(
        self, query: str, mode: str = "local",
        limit: int = 10, offset: int = 0,
        type: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        domain: Optional[str] = None
    ) -> RetrieveResult:
        """检索认知 — 路由与 inject 对称"""
        if domain is not None:
            self._validate_domain(domain)

        filters = {}
        if type:
            filters["type"] = type
        if tags:
            filters["tags"] = tags
        if min_confidence > 0:
            filters["min_confidence"] = min_confidence
        if domain:
            filters["domain"] = domain

        backend = self._resolve_backend_for_retrieve(domain)
        try:
            adapter = self._registry.get(backend)
            raw = await adapter.retrieve(
                query=query, mode=mode, limit=limit + offset, filters=filters
            )
        except _ADAPTER_INTERNAL_EXCEPTIONS as e:
            raise _wrap_adapter_error("retrieve", e)

        return RetrieveResult(
            items=raw.items[offset:offset + limit],
            total=raw.total,
            has_more=offset + limit < raw.total,
        )

    async def update(
        self, cognition_id: str, content: str,
        metadata: Dict
    ) -> UpdateResult:
        """更新认知 — 通过映射找到正确后端"""
        self._poison_check(content)
        backend = self._find_backend_for_cognition(cognition_id)
        try:
            adapter = self._registry.get(backend)
            return await adapter.update(cognition_id, content, metadata)
        except _ADAPTER_INTERNAL_EXCEPTIONS as e:
            raise _wrap_adapter_error("update", e)

    async def delete(self, cognition_id: str) -> bool:
        """删除认知 — 通过映射找到正确后端"""
        backend = self._find_backend_for_cognition(cognition_id)
        try:
            adapter = self._registry.get(backend)
            success = await adapter.delete(cognition_id)
        except _ADAPTER_INTERNAL_EXCEPTIONS as e:
            raise _wrap_adapter_error("delete", e)

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
        """列出所有后端及其状态"""
        return self._registry.get_status_all()

    def get_active_backend(self) -> str:
        """获取当前活跃后端"""
        return self._active_backend or self._registry.auto_select()

    def get_domain_routing(self) -> Dict[str, str]:
        """获取领域路由配置"""
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

    async def _find_by_content_hash(
        self, content_hash: str,
        domain: Optional[str] = None
    ) -> Optional[CognitionInput]:
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
        raise UnknownBackendError(cognition_id)

    def _get_db_engine(self) -> Engine:
        """获取数据库引擎（懒加载单例）"""
        if self._db_engine is None:
            import os
            db_path = os.environ.get("SQLITE_PATH") or str(Path(__file__).resolve().parents[5] / "data" / "reins.db")
            self._db_engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False}
            )
        return self._db_engine

    def _record_backend_mapping(self, cognition_id: str, backend: str):
        """写入映射 — P0-1: LRU 缓存 + DB 持久化"""
        if cognition_id in self._backend_map:
            self._backend_map.move_to_end(cognition_id)
        self._backend_map[cognition_id] = backend
        while len(self._backend_map) > self._BACKEND_MAP_MAX_SIZE:
            self._backend_map.popitem(last=False)  # 淘汰最旧
        
        # 写入 DB
        try:
            engine = self._get_db_engine()
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT OR REPLACE INTO cognition_backend_map (cognition_id, backend_name, created_at, updated_at)
                    VALUES (:cognition_id, :backend_name, datetime('now'), datetime('now'))
                """), {
                    "cognition_id": cognition_id,
                    "backend_name": backend,
                })
        except Exception as e:
            logger.warning(f"[GraspFacade] 写入 backend mapping 到 DB 失败: {e}")

    def _remove_backend_mapping(self, cognition_id: str):
        """删除映射 - 从 LRU 缓存和 DB"""
        self._backend_map.pop(cognition_id, None)
        try:
            engine = self._get_db_engine()
            with engine.begin() as conn:
                conn.execute(text("""
                    DELETE FROM cognition_backend_map WHERE cognition_id = :cognition_id
                """), {"cognition_id": cognition_id})
        except Exception as e:
            logger.warning(f"[GraspFacade] 删除 backend mapping 失败: {e}")

    def _load_backend_from_db(self, cognition_id: str) -> Optional[str]:
        """从 DB 加载后端映射"""
        try:
            engine = self._get_db_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT backend_name FROM cognition_backend_map WHERE cognition_id = :cognition_id
                """), {"cognition_id": cognition_id}).fetchone()
                if result:
                    return result[0]
        except Exception as e:
            logger.warning(f"[GraspFacade] 从 DB 加载 backend mapping 失败: {e}")
        return None

    def _validate_content(self, content: str):
        """验证内容不为空"""
        if not content or not content.strip():
            raise NexusException(
                code=ErrorCode.GRASP_INVALID_CONTENT,
                message="认知内容不能为空"
            )

    def _poison_check(self, content: str):
        """毒药检测"""
        is_poison, risks = self._poison.detect(content)
        if is_poison:
            raise NexusException(
                code=ErrorCode.GRASP_POISON_DETECTED,
                message="检测到认知投毒，请求已被拒绝",
                details={"risk_factors": risks},
            )

    def _quality_score(self, input: CognitionInput) -> float:
        """计算质量评分"""
        is_valid, score, _ = self._validator.validate(
            input.content, input.confidence
        )
        return max(0, score)
