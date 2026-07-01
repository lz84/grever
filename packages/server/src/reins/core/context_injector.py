"""Context injector — re-exports + ContextInjector (main class)."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import time

from loguru import logger

from ._ci_models import TaskStatus, CONTEXT_TEMPLATES, LRUCache
from ._ci_query import ContextQuery, ContextResult, GraspAdapter


@dataclass
class InjectionConfig:
    """注入配置"""
    max_context_size: int = 5000
    max_cognitions: int = 10
    max_tokens: int = 2000
    include_task_metadata: bool = True
    confidence_threshold: float = 0.6
    cache_max_size: int = 100
    cache_ttl_seconds: int = 300
    enable_batch_injection: bool = True
    batch_size: int = 10


class ContextInjector:
    """上下文注入器 — 基于任务状态的动态上下文注入"""

    def __init__(self, max_cache_size: int = 100, default_ttl_seconds: int = 300,
                 config: Optional[InjectionConfig] = None):
        self.config = config or InjectionConfig()
        self.cache = LRUCache(max_size=max_cache_size, default_ttl_seconds=default_ttl_seconds)
        self.grasp_adapter = GraspAdapter()
        self._total_injections = 0
        self._cache_hits = 0
        self._total_retrieval_time_ms = 0.0

    def _generate_cache_key(self, query: ContextQuery, cognition_version: Optional[str] = None) -> str:
        version = cognition_version or self.grasp_adapter.get_cognition_version()
        return ":".join([query.task_id, query.agent_id or "any", query.status.value, version])

    def _truncate_to_size(self, text: str, max_size: int) -> str:
        if len(text) <= max_size:
            return text
        return text[:max_size - 200] + "\n\n[内容已截断,剩余部分被省略...]"

    def _build_prompt_with_context(self, task: Any, cognitions: List[dict],
                                   sections: Dict[str, List[dict]],
                                   cache_hit: bool = False,
                                   status: TaskStatus = TaskStatus.TODO) -> str:
        lines = []
        template = CONTEXT_TEMPLATES.get(status, CONTEXT_TEMPLATES[TaskStatus.TODO])
        lines.extend([f"# {task.title}", f"任务 ID: {task.id}"])
        if getattr(task, 'description', None):
            lines.append(f"描述:{task.description}")
        if getattr(task, 'assigned_agent', None):
            lines.append(f"分配给:{task.assigned_agent}")
        if getattr(task, 'status', None):
            lines.append(f"状态:{task.status.value}")
        lines.extend(["", f"## {template.title}", template.instructions, ""])
        if sections:
            lines.append(f"## 相关知识 ({len(cognitions)} 条)")
            for section_title, section_cognitions in sections.items():
                lines.extend([f"### {section_title}", "-" * 40])
                for i, cognition in enumerate(section_cognitions, 1):
                    conf = cognition.get("confidence", 0)
                    ctype = cognition.get("type", "unknown")
                    content = cognition.get("content", "")
                    lines.extend([f"[{i}] 类型:{ctype} | 置信度:{conf:.2f}", content, ""])
            lines.append("")
        if cache_hit:
            lines.append("/// 缓存命中 ///")
        lines.append("/// 任务结束 ///")
        prompt = "\n".join(lines)
        return self._truncate_to_size(prompt, self.config.max_context_size)

    async def inject_for_task(self, task: Any, query: Optional[ContextQuery] = None) -> str:
        if query is None:
            status = getattr(task, 'status', TaskStatus.TODO)
            if isinstance(status, str):
                status = TaskStatus(status)
            query = ContextQuery(
                task_id=task.id, task_title=task.title,
                task_description=getattr(task, 'description', None),
                input_data=getattr(task, 'input_data', {}),
                agent_id=getattr(task, 'assigned_agent', None) or getattr(task, 'assigned_agent_id', None),
                status=status,
            )
        cognition_version = self.grasp_adapter.get_cognition_version()
        start_time = time.time()
        cognitions = await self.grasp_adapter.retrieve(
            query=query.to_query_string(), domain=query.domain,
            limit=self.config.max_cognitions, min_confidence=self.config.confidence_threshold,
        )
        retrieval_time = (time.time() - start_time) * 1000
        self._total_retrieval_time_ms += retrieval_time
        sections = self._group_by_section(cognitions, query.status)
        self._total_injections += 1
        prompt = self._build_prompt_with_context(task, cognitions, sections, cache_hit=False, status=query.status)
        logger.info(f"Context injected for task {task.id} ({query.status.value}): "
                    f"{len(cognitions)} cognitions, {retrieval_time:.2f}ms, cache_miss")
        return prompt

    def _group_by_section(self, cognitions: List[dict], status: TaskStatus) -> Dict[str, List[dict]]:
        template = CONTEXT_TEMPLATES.get(status, CONTEXT_TEMPLATES[TaskStatus.TODO])
        sections = {s: [] for s in template.sections}
        for cognition in cognitions:
            content = cognition.get("content", "").lower()
            ctype = cognition.get("type", "")
            assigned = template.sections[0]
            if "方法" in content or "步骤" in content or ctype == "pattern":
                assigned = next((s for s in template.sections if "执行" in s), assigned)
            elif "教训" in content or "反思" in content or ctype == "lesson":
                assigned = next((s for s in template.sections if "经验" in s or "教训" in s), assigned)
            elif "目标" in content or "需求" in content or ctype == "fact":
                assigned = next((s for s in template.sections if "目标" in s or "领域" in s), assigned)
            if assigned in sections:
                sections[assigned].append(cognition)
        return sections

    async def batch_inject(self, tasks: List[Any]) -> Dict[str, str]:
        if not self.config.enable_batch_injection:
            return {t.id: await self.inject_for_task(t) for t in tasks}
        cognitions_by_q = {}
        for task in tasks:
            status = getattr(task, 'status', TaskStatus.TODO)
            if isinstance(status, str):
                status = TaskStatus(status)
            query = ContextQuery(
                task_id=task.id, task_title=task.title,
                task_description=getattr(task, 'description', None),
                input_data=getattr(task, 'input_data', {}),
                agent_id=getattr(task, 'assigned_agent', None) or getattr(task, 'assigned_agent_id', None),
                status=status,
            )
            qs = query.to_query_string()
            if qs not in cognitions_by_q:
                cognitions_by_q[qs] = []
            cognitions_by_q[qs].append(query)
        start_time = time.time()
        batch = await self.grasp_adapter.batch_retrieve(list(cognitions_by_q.keys()), limit=self.config.max_cognitions)
        retrieval_time = (time.time() - start_time) * 1000
        results = {}
        for task in tasks:
            status = getattr(task, 'status', TaskStatus.TODO)
            if isinstance(status, str):
                status = TaskStatus(status)
            cognitions = batch.get(task.title, [])
            sections = self._group_by_section(cognitions, status)
            results[task.id] = self._build_prompt_with_context(task, cognitions, sections, cache_hit=False, status=status)
        logger.info(f"Batch context injection: {len(tasks)} tasks, {retrieval_time:.2f}ms")
        return results

    def get_stats(self) -> dict:
        cache_stats = self.cache.get_stats()
        avg_rt = self._total_retrieval_time_ms / self._total_injections if self._total_injections > 0 else 0.0
        return {"total_injections": self._total_injections, "cache_hits": self._cache_hits,
                "cache": cache_stats, "avg_retrieval_time_ms": avg_rt,
                "latency_check": "PASS" if avg_rt < 100 else "WARN",
                "hit_rate_check": "PASS" if cache_stats["hit_rate"] > 0.8 else "WARN"}

    async def invalidate_cache(self, task_id: str, new_status: TaskStatus):
        logger.debug(f"Cache invalidation requested for task {task_id} -> {new_status.value} (cache disabled)")

    async def cleanup(self):
        logger.debug("Context injector cleanup: cache disabled, no-op")


__all__ = [
    "TaskStatus", "ContextTemplate", "CONTEXT_TEMPLATES", "CacheEntry", "LRUCache",
    "ContextQuery", "ContextResult", "GraspAdapter",
    "InjectionConfig", "ContextInjector",
]
