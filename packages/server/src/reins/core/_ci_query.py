"""Context injector — query/result models + Grasp adapter."""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from loguru import logger
from ._ci_models import TaskStatus


@dataclass
class ContextQuery:
    """上下文查询"""
    task_id: str
    task_title: str
    task_description: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    domain: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    similar_task_ids: List[str] = field(default_factory=list)

    def to_query_string(self) -> str:
        parts = [self.task_title]
        if self.task_description:
            parts.append(self.task_description)
        status_queries = {
            TaskStatus.TODO: "任务目标 任务背景 需求分析",
            TaskStatus.IN_PROGRESS: "执行方法 技术实现 解决方案 调试经验",
            TaskStatus.DONE: "结果验证 经验总结 教训反思 后续建议",
        }
        parts.append(status_queries.get(self.status, ""))
        return " ".join(filter(None, parts))

    def to_cache_key(self) -> str:
        return ":".join([self.task_id, self.agent_id or "any", self.status.value])


@dataclass
class ContextResult:
    """上下文查询结果"""
    query: ContextQuery
    cognitions: List[dict]
    retrieval_time_ms: float
    cache_hit: bool = False
    cache_key: Optional[str] = None
    sections: Dict[str, List[dict]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": {"task_id": self.query.task_id, "task_title": self.query.task_title,
                      "domain": self.query.domain, "status": self.query.status.value},
            "cognitions": self.cognitions, "sections": self.sections,
            "retrieval_time_ms": self.retrieval_time_ms,
            "cache_hit": self.cache_hit, "cache_key": self.cache_key,
        }


class GraspAdapter:
    """Grasp 适配器 — 提供与 Grasp 服务的接口"""

    def __init__(self, service=None):
        self._service = service
        self._service_initialized = False
        if service is None:
            try:
                from grasp.common.service import GraspService
                self._service = GraspService(storage_backend="memory")
                self._service_initialized = True
                logger.info("GraspAdapter initialized with memory service")
            except Exception as e:
                logger.warning(f"Failed to initialize GraspService: {e}")
                self._service = None

    async def retrieve(self, query: str, domain: Optional[str] = None,
                      limit: int = 10, min_confidence: float = 0.5) -> List[dict]:
        """从 Grasp 检索认知。"""
        if self._service is None:
            return []
        try:
            from grasp.common.models import CognitionType
        except ImportError:
            return []
        type_filter = None
        if domain:
            type_map = {"technical": CognitionType.PATTERN,
                         "business": CognitionType.FACT, "strategy": CognitionType.META}
            type_filter = [type_map.get(domain, CognitionType.FACT)]
        try:
            result = self._service.retrieve(query=query, type=type_filter,
                                          min_confidence=min_confidence, limit=limit)
            return [c.to_dict() for c in result.items]
        except Exception as e:
            logger.error(f"Grasp retrieval error: {e}")
            return []

    async def batch_retrieve(self, queries: List[str], domain: Optional[str] = None,
                            limit: int = 10) -> Dict[str, List[dict]]:
        """批量检索认知。"""
        tasks = [self.retrieve(q, domain=domain, limit=limit) for q in queries]
        resolved = await asyncio.gather(*tasks)
        return {q: c for q, c in zip(queries, resolved)}

    def get_cognition_version(self) -> str:
        """获取当前认知库版本号。"""
        if not self._service:
            return "0"
        try:
            return str(len(self._service.list_cognitions(limit=10000)))
        except Exception:
            return "0"
