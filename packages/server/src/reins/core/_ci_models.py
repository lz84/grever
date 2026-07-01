"""Context injector — models: TaskStatus, ContextTemplate, CacheEntry, LRUCache."""
import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any


class TaskStatus(str, Enum):
    """任务状态枚举"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    PAUSED = "paused"


@dataclass
class ContextTemplate:
    """上下文模板"""
    title: str
    instructions: str
    sections: List[str]


CONTEXT_TEMPLATES: Dict[TaskStatus, ContextTemplate] = {
    TaskStatus.TODO: ContextTemplate(
        title="任务准备阶段",
        instructions="为即将开始的任务提供目标和背景认知",
        sections=["任务目标与期望结果", "相关领域知识", "类似任务的经验参考"],
    ),
    TaskStatus.IN_PROGRESS: ContextTemplate(
        title="任务执行阶段",
        instructions="为正在执行的任务提供执行指南和实时经验",
        sections=["执行步骤和方法论", "相似任务的解决方案", "当前任务的约束条件", "常见陷阱和规避方法"],
    ),
    TaskStatus.DONE: ContextTemplate(
        title="任务完成阶段",
        instructions="为已完成的任务提供总结和未来建议",
        sections=["结果验证清单", "经验总结与教训", "后续行动建议", "知识归档指引"],
    ),
}


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    status: Optional[str] = None
    cognition_version: Optional[str] = None

    def is_expired(self, ttl_seconds: int) -> bool:
        return datetime.now() - self.created_at > timedelta(seconds=ttl_seconds)

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


class LRUCache:
    """LRU 缓存 + TTL 过期"""

    def __init__(self, max_size: int = 100, default_ttl_seconds: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    async def get(self, key: str, status: Optional[str] = None,
                  cognition_version: Optional[str] = None,
                  ttl: Optional[int] = None) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            ttl = ttl or self.default_ttl
            if key not in self._cache:
                self._misses += 1
                return None
            entry = self._cache[key]
            if entry.status is not None and entry.status != status:
                del self._cache[key]; self._invalidations += 1; self._misses += 1; return None
            if entry.cognition_version is not None and entry.cognition_version != cognition_version:
                del self._cache[key]; self._invalidations += 1; self._misses += 1; return None
            if entry.is_expired(ttl):
                del self._cache[key]; self._misses += 1; return None
            self._cache.move_to_end(key)
            entry.last_accessed = datetime.now()
            self._hits += 1
            return entry.value

    async def set(self, key: str, value: Any, status: Optional[str] = None,
                  cognition_version: Optional[str] = None, ttl: Optional[int] = None):
        """设置缓存值"""
        async with self._lock:
            ttl = ttl or self.default_ttl
            if key in self._cache:
                del self._cache[key]
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False); self._evictions += 1
            self._cache[key] = CacheEntry(key=key, value=value,
                                          status=status, cognition_version=cognition_version)

    async def delete(self, key: str):
        """删除缓存值"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def invalidate_by_status(self, task_id: str, new_status: str):
        """基于任务状态失效缓存"""
        async with self._lock:
            keys = [k for k, e in self._cache.items()
                    if k.startswith(f"{task_id}:") and
                    (e.status == new_status or e.cognition_version is not None)]
            for key in keys:
                del self._cache[key]; self._invalidations += 1

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        return {"size": len(self._cache), "max_size": self.max_size,
                "hits": self._hits, "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "evictions": self._evictions, "invalidations": self._invalidations}

    def cleanup_expired(self, ttl: Optional[int] = None) -> int:
        """清理过期条目"""
        ttl = ttl or self.default_ttl
        keys = [k for k, e in self._cache.items() if e.is_expired(ttl)]
        for k in keys:
            del self._cache[k]
        return len(keys)
