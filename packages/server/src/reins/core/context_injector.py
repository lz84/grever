"""
Reins Server - 上下文注入服务 (Sprint 2 Enhanced)

功能:
- 基于任务状态的动态上下文注入 (SP2-16)
  - todo: 注入任务目标和相关认知
  - in_progress: 注入执行指南和相似任务经验
  - done: 注入结果总结和后续建议
- LRU 缓存 + TTL 过期策略 (SP2-17)
  - 缓存键:task_id + agent_id + status
  - 失效条件:任务状态变更、认知更新、超过 TTL
  - 缓存监控指标
- 上下文大小控制 (token 限制)
- 上下文注入延迟 < 100ms(缓存命中)
- 缓存命中率 > 80%

实现者:蚊子-Sprint2-上下文注入
"""

import asyncio
from loguru import logger
import time
import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

# ============================================================================
# 任务状态上下文模板
# ============================================================================

class TaskStatus(str, Enum):
    """任务状态枚举(与 reins/models/task.py 保持一致)"""
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
    sections: List[str]  # 应该包含的内容 section 标题

# 不同状态下的上下文模板
CONTEXT_TEMPLATES: Dict[TaskStatus, ContextTemplate] = {
    TaskStatus.TODO: ContextTemplate(
        title="任务准备阶段",
        instructions="为即将开始的任务提供目标和背景认知",
        sections=[
            "任务目标与期望结果",
            "相关领域知识",
            "类似任务的经验参考",
        ]
    ),
    TaskStatus.IN_PROGRESS: ContextTemplate(
        title="任务执行阶段",
        instructions="为正在执行的任务提供执行指南和实时经验",
        sections=[
            "执行步骤和方法论",
            "相似任务的解决方案",
            "当前任务的约束条件",
            "常见陷阱和规避方法",
        ]
    ),
    TaskStatus.DONE: ContextTemplate(
        title="任务完成阶段",
        instructions="为已完成的任务提供总结和未来建议",
        sections=[
            "结果验证清单",
            "经验总结与教训",
            "后续行动建议",
            "知识归档指引",
        ]
    ),
}

# ============================================================================
# 缓存实现
# ============================================================================

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    status: Optional[str] = None  # 任务状态,用于失效判断
    cognition_version: Optional[str] = None  # 认知版本,用于失效判断

    def is_expired(self, ttl_seconds: int) -> bool:
        """检查是否过期"""
        return datetime.now() - self.created_at > timedelta(seconds=ttl_seconds)

    @property
    def age_seconds(self) -> float:
        """获取缓存年龄(秒)"""
        return (datetime.now() - self.created_at).total_seconds()

class LRUCache:
    """
    LRU 缓存 + TTL 过期

    功能:
    - 固定容量 LRU 淘汰
    - TTL 自动过期
    - 访问更新最近使用时间
    - 基于状态的失效判断
    """

    def __init__(self, max_size: int = 100, default_ttl_seconds: int = 300):
        """
        :param max_size: 最大缓存条目数
        :param default_ttl_seconds: 默认 TTL(秒)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

        # 统计
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    async def get(self, key: str,
                  status: Optional[str] = None,
                  cognition_version: Optional[str] = None,
                  ttl: Optional[int] = None) -> Optional[Any]:
        """
        获取缓存值

        :param key: 缓存键
        :param status: 当前任务状态(用于失效判断)
        :param cognition_version: 当前认知版本(用于失效判断)
        :param ttl: 超时时间
        :return: 缓存值或 None
        """
        async with self._lock:
            ttl = ttl or self.default_ttl

            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 检查状态失效
            if entry.status is not None and entry.status != status:
                del self._cache[key]
                self._invalidations += 1
                self._misses += 1
                return None

            # 检查认知版本失效
            if entry.cognition_version is not None and entry.cognition_version != cognition_version:
                del self._cache[key]
                self._invalidations += 1
                self._misses += 1
                return None

            # 检查过期
            if entry.is_expired(ttl):
                del self._cache[key]
                self._misses += 1
                return None

            # 更新访问时间和 LRU 位置
            self._cache.move_to_end(key)
            entry.last_accessed = datetime.now()
            self._hits += 1

            return entry.value

    async def set(self, key: str, value: Any,
                  status: Optional[str] = None,
                  cognition_version: Optional[str] = None,
                  ttl: Optional[int] = None):
        """设置缓存值"""
        async with self._lock:
            ttl = ttl or self.default_ttl

            # 如果已存在,删除旧条目
            if key in self._cache:
                del self._cache[key]

            # LRU 淘汰
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._evictions += 1

            # 添加新条目
            entry = CacheEntry(
                key=key,
                value=value,
                status=status,
                cognition_version=cognition_version
            )
            self._cache[key] = entry

    async def delete(self, key: str):
        """删除缓存值"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def invalidate_by_status(self, task_id: str, new_status: str):
        """
        基于任务状态失效缓存

        :param task_id: 任务 ID
        :param new_status: 新状态
        """
        async with self._lock:
            # 找到所有相关缓存
            keys_to_remove = []
            for key in self._cache:
                if key.startswith(f"{task_id}:"):
                    entry = self._cache[key]
                    # 如果状态匹配或认知版本匹配,则失效
                    if entry.status == new_status or entry.cognition_version is not None:
                        keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]
                self._invalidations += 1

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "invalidations": self._invalidations,
        }

    def cleanup_expired(self, ttl: Optional[int] = None) -> int:
        """
        清理过期条目(定期调用)

        :return: 清理的条目数
        """
        ttl = ttl or self.default_ttl
        removed = 0

        keys_to_remove = []
        for key, entry in self._cache.items():
            if entry.is_expired(ttl):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            removed += 1

        return removed

# ============================================================================
# 认知查询器
# ============================================================================

@dataclass
class ContextQuery:
    """上下文查询"""
    task_id: str
    task_title: str
    task_description: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    domain: Optional[str] = None  # 领域过滤
    status: TaskStatus = TaskStatus.TODO  # 任务状态
    similar_task_ids: List[str] = field(default_factory=list)  # 相似任务 ID 列表

    def to_query_string(self) -> str:
        """生成查询字符串"""
        parts = [self.task_title]
        if self.task_description:
            parts.append(self.task_description)

        # 根据状态添加特定查询词
        status_queries = {
            TaskStatus.TODO: "任务目标 任务背景 需求分析",
            TaskStatus.IN_PROGRESS: "执行方法 技术实现 解决方案 调试经验",
            TaskStatus.DONE: "结果验证 经验总结 教训反思 后续建议",
        }
        parts.append(status_queries.get(self.status, ""))

        return " ".join(filter(None, parts))

    def to_cache_key(self) -> str:
        """生成缓存键"""
        # 缓存键:task_id + agent_id + status + cognition_version
        key_parts = [
            self.task_id,
            self.agent_id or "any",
            self.status.value,
        ]
        return ":".join(key_parts)

@dataclass
class ContextResult:
    """上下文查询结果"""
    query: ContextQuery
    cognitions: List[dict]  # Grasp 认知列表
    retrieval_time_ms: float
    cache_hit: bool = False
    cache_key: Optional[str] = None
    sections: Dict[str, List[dict]] = field(default_factory=dict)  # 按 section 分组

    def to_dict(self) -> dict:
        return {
            "query": {
                "task_id": self.query.task_id,
                "task_title": self.query.task_title,
                "domain": self.query.domain,
                "status": self.query.status.value,
            },
            "cognitions": self.cognitions,
            "sections": self.sections,
            "retrieval_time_ms": self.retrieval_time_ms,
            "cache_hit": self.cache_hit,
            "cache_key": self.cache_key,
        }

class GraspAdapter:
    """
    Grasp 适配器

    提供与 Grasp 服务的接口
    当前使用内存服务实现,后续可切换为 HTTP API
    """

    def __init__(self, service=None):
        """
        :param service: GraspService 实例,None 则使用默认内存服务
        """
        self._service = service
        self._service_initialized = False

        # 延迟导入,避免循环依赖
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
        """
        从 Grasp 检索认知

        :param query: 查询文本
        :param domain: 领域过滤
        :param limit: 最大返回数量
        :param min_confidence: 最低置信度
        :return: 认知列表
        """
        # 如果服务未初始化,返回空结果
        if self._service is None:
            return []

        # 导入类型
        try:
            from grasp.common.models import CognitionType
        except ImportError:
            return []

        type_filter = None
        if domain:
            # 根据领域映射认知类型
            type_map = {
                "technical": CognitionType.PATTERN,
                "business": CognitionType.FACT,
                "strategy": CognitionType.META,
            }
            type_filter = [type_map.get(domain, CognitionType.FACT)]

        try:
            # 检索
            result = self._service.retrieve(
                query=query,
                type=type_filter,
                min_confidence=min_confidence,
                limit=limit,
            )

            # 转换为字典
            return [c.to_dict() for c in result.items]
        except Exception as e:
            logger.error(f"Grasp retrieval error: {e}")
            return []

    async def batch_retrieve(self, queries: List[str], domain: Optional[str] = None,
                            limit: int = 10) -> Dict[str, List[dict]]:
        """
        批量检索认知(优化:减少 Grasp 调用)

        :param queries: 查询文本列表
        :param domain: 领域过滤
        :param limit: 最大返回数量
        :return: 查询 -> 认知列表的映射
        """
        results = {}

        # 并发检索
        tasks = [self.retrieve(q, domain=domain, limit=limit) for q in queries]
        resolved_queries = await asyncio.gather(*tasks)

        for query, cognitions in zip(queries, resolved_queries):
            results[query] = cognitions

        return results

    def get_cognition_version(self) -> str:
        """
        获取当前认知库的版本号

        用于缓存失效判断
        """
        if not self._service:
            return "0"

        try:
            # 使用认知数量作为简单版本标识
            cognitions = self._service.list_cognitions(limit=10000)
            return str(len(cognitions))
        except:
            return "0"

# ============================================================================
# 上下文注入器
# ============================================================================

@dataclass
class InjectionConfig:
    """注入配置"""
    # 大小控制
    max_context_size: int = 5000  # 最大上下文大小(字符)
    max_cognitions: int = 10  # 最大认知数量
    max_tokens: int = 2000  # 最大 tokens(用于 LLM 限制)

    # 内容控制
    include_task_metadata: bool = True
    confidence_threshold: float = 0.6  # 置信度阈值

    # 缓存配置
    cache_max_size: int = 100  # 缓存最大条目数
    cache_ttl_seconds: int = 300  # 缓存 TTL(秒)

    # 性能优化
    enable_batch_injection: bool = True  # 启用批量注入
    batch_size: int = 10  # 批量大小

class ContextInjector:
    """
    上下文注入器 (Sprint 2 Enhanced)

    功能:
    - 任务启动时查询 Grasp (SP2-15)
    - 基于任务状态的动态上下文 (SP2-16)
      - todo: 注入任务目标和相关认知
      - in_progress: 注入执行指南和相似任务经验
      - done: 注入结果总结和后续建议
    - LRU 缓存 + TTL 过期 + 状态失效 (SP2-17)
    - 批量查询优化
    """

    def __init__(self,
                 max_cache_size: int = 100,
                 default_ttl_seconds: int = 300,
                 config: Optional[InjectionConfig] = None):
        """
        :param max_cache_size: 缓存最大容量
        :param default_ttl_seconds: 默认 TTL
        :param config: 注入配置
        """
        self.config = config or InjectionConfig()
        self.cache = LRUCache(
            max_size=max_cache_size,
            default_ttl_seconds=default_ttl_seconds
        )
        self.grasp_adapter = GraspAdapter()

        # 统计
        self._total_injections = 0
        self._cache_hits = 0
        self._total_retrieval_time_ms = 0.0

    def _generate_cache_key(self, query: ContextQuery,
                           cognition_version: Optional[str] = None) -> str:
        """
        生成缓存 key

        缓存键格式:task_id:agent_id:status:cognition_version
        """
        version = cognition_version or self.grasp_adapter.get_cognition_version()
        key_parts = [
            query.task_id,
            query.agent_id or "any",
            query.status.value,
            version,
        ]
        return ":".join(key_parts)

    def _estimate_tokens(self, text: str) -> int:
        """
        估算 tokens 数量

        简化估算:每 4 个字符约等于 1 token
        """
        return len(text) // 4

    def _truncate_to_size(self, text: str, max_size: int) -> str:
        """
        截断文本到指定大小

        :param text: 原文本
        :param max_size: 最大字符数
        :return: 截断后的文本
        """
        if len(text) <= max_size:
            return text

        # 保留最后 200 字符作为省略号
        return text[:max_size - 200] + "\n\n[内容已截断,剩余部分被省略...]"

    def _build_prompt_with_context(self, task: Any,
                                   cognitions: List[dict],
                                   sections: Dict[str, List[dict]],
                                   cache_hit: bool = False,
                                   status: TaskStatus = TaskStatus.TODO) -> str:
        """
        构建带上下文的 Agent 提示词(基于任务状态)

        :param task: 任务对象
        :param cognitions: 检索到的认知
        :param sections: 按 section 分组的认知
        :param cache_hit: 是否缓存命中
        :param status: 任务状态
        :return: 提示词文本
        """
        lines = []
        template = CONTEXT_TEMPLATES.get(status, CONTEXT_TEMPLATES[TaskStatus.TODO])

        # 任务基本信息
        lines.append(f"# {task.title}")
        lines.append(f"任务 ID: {task.id}")
        if hasattr(task, 'description') and task.description:
            lines.append(f"描述:{task.description}")
        if hasattr(task, 'assigned_agent') and task.assigned_agent:
            lines.append(f"分配给:{task.assigned_agent}")
        if hasattr(task, 'status'):
            lines.append(f"状态:{task.status.value}")
        lines.append("")

        # 当前阶段说明
        lines.append(f"## {template.title}")
        lines.append(template.instructions)
        lines.append("")

        # 检索到的认知(按 section 分组)
        if sections:
            lines.append(f"## 相关知识 ({len(cognitions)} 条)")
            lines.append("")

            for section_title, section_cognitions in sections.items():
                lines.append(f"### {section_title}")
                lines.append("-" * 40)

                for i, cognition in enumerate(section_cognitions, 1):
                    confidence = cognition.get("confidence", 0)
                    cogn_type = cognition.get("type", "unknown")
                    content = cognition.get("content", "")

                    lines.append(f"[{i}] 类型:{cogn_type} | 置信度:{confidence:.2f}")
                    lines.append(content)
                    lines.append("")

            lines.append("")

        # 缓存信息
        if cache_hit:
            lines.append("/// 缓存命中 ///")

        # 任务结束标记
        lines.append("/// 任务结束 ///")

        # 构建完整提示词
        prompt = "\n".join(lines)

        # 截断到最大大小
        prompt = self._truncate_to_size(prompt, self.config.max_context_size)

        return prompt

    async def inject_for_task(self, task: Any,
                             query: Optional[ContextQuery] = None) -> str:
        """
        为任务注入上下文 (SP2-15, SP2-16)

        :param task: 任务对象
        :param query: 查询对象(可选,用于自定义查询)
        :return: 注入后的提示词
        """
        # 生成查询
        if query is None:
            # 从 task 对象提取属性
            status = getattr(task, 'status', TaskStatus.TODO)
            if isinstance(status, str):
                status = TaskStatus(status)

            query = ContextQuery(
                task_id=task.id,
                task_title=task.title,
                task_description=getattr(task, 'description', None),
                input_data=getattr(task, 'input_data', {}),
                agent_id=getattr(task, 'assigned_agent', None) or getattr(task, 'assigned_agent_id', None),
                status=status,
            )

        # 获取认知版本
        cognition_version = self.grasp_adapter.get_cognition_version()

        # 生成缓存 key（缓存已禁用，所有请求直接查 Grasp，保持数据一致性）
        cache_key = self._generate_cache_key(query, cognition_version)

        # 跳过缓存：直接查询 Grasp（确保数据源自数据库，无内存缓存）
        cached_result = None

        # 查询 Grasp
        start_time = time.time()
        query_string = query.to_query_string()

        cognitions = await self.grasp_adapter.retrieve(
            query=query_string,
            domain=query.domain,
            limit=self.config.max_cognitions,
            min_confidence=self.config.confidence_threshold,
        )

        retrieval_time = (time.time() - start_time) * 1000
        self._total_retrieval_time_ms += retrieval_time

        # 按 section 分组
        sections = self._group_by_section(cognitions, query.status)

        # 缓存已禁用：每次都直接查 Grasp，确保数据一致性
        # await self.cache.set(cache_key, {...})  # 禁用内存缓存

        self._total_injections += 1

        # 构建提示词
        prompt = self._build_prompt_with_context(
            task, cognitions, sections, cache_hit=False, status=query.status
        )

        logger.info(
            f"Context injected for task {task.id} ({query.status.value}): "
            f"{len(cognitions)} cognitions, {retrieval_time:.2f}ms, cache_miss"
        )

        return prompt

    def _group_by_section(self, cognitions: List[dict], 
                         status: TaskStatus) -> Dict[str, List[dict]]:
        """
        将认知按 section 分组

        :param cognitions: 认知列表
        :param status: 任务状态
        :return: section -> 认知列表的映射
        """
        template = CONTEXT_TEMPLATES.get(status, CONTEXT_TEMPLATES[TaskStatus.TODO])
        sections = {section: [] for section in template.sections}

        # 简单启发式分组（根据认知内容和标签）
        for cognition in cognitions:
            content = cognition.get("content", "").lower()
            tags = cognition.get("tags", [])
            cogn_type = cognition.get("type", "")
            
            # 默认分配到第一个 section
            assigned_section = template.sections[0]
            
            # 根据内容和标签进行启发式分组
            if "方法" in content or "步骤" in content or cogn_type == "pattern":
                if "执行方法" in template.sections:
                    assigned_section = "执行方法"
                elif "执行步骤和方法论" in template.sections:
                    assigned_section = "执行步骤和方法论"
            elif "教训" in content or "反思" in content or cogn_type == "lesson":
                if "经验总结" in template.sections:
                    assigned_section = "经验总结"
                elif "教训反思" in template.sections:
                    assigned_section = "教训反思"
            elif "目标" in content or "需求" in content or cogn_type == "fact":
                if "任务目标" in template.sections:
                    assigned_section = "任务目标与期望结果"
                elif "相关领域知识" in template.sections:
                    assigned_section = "相关领域知识"
            
            if assigned_section in sections:
                sections[assigned_section].append(cognition)
        
        return sections

    async def batch_inject(self, tasks: List[Any]) -> Dict[str, str]:
        """
        批量注入上下文(优化:批量查询)(SP2-17)

        :param tasks: 任务列表
        :return: 任务 ID -> 提示词的映射
        """
        if not self.config.enable_batch_injection:
            # 逐个注入
            return {
                task.id: await self.inject_for_task(task)
                for task in tasks
            }

        # 构建批量查询
        cognitions_by_query = {}
        tasks_by_query = {}

        for task in tasks:
            status = getattr(task, 'status', TaskStatus.TODO)
            if isinstance(status, str):
                status = TaskStatus(status)

            query = ContextQuery(
                task_id=task.id,
                task_title=task.title,
                task_description=getattr(task, 'description', None),
                input_data=getattr(task, 'input_data', {}),
                agent_id=getattr(task, 'assigned_agent', None) or getattr(task, 'assigned_agent_id', None),
                status=status,
            )

            qs = query.to_query_string()
            if qs not in cognitions_by_query:
                cognitions_by_query[qs] = []
                tasks_by_query[qs] = []
            cognitions_by_query[qs].append(query)
            tasks_by_query[qs].append(task)

        # 批量检索
        start_time = time.time()
        cognitions_batch = await self.grasp_adapter.batch_retrieve(
            list(cognitions_by_query.keys()),
            limit=self.config.max_cognitions,
        )
        retrieval_time = (time.time() - start_time) * 1000

        # 缓存结果
        for query_string, query_list in cognitions_by_query.items():
            cognitions = cognitions_batch.get(query_string, [])
            status = query_list[0].status

            # 按 section 分组
            sections = self._group_by_section(cognitions, status)

            # 缓存每个查询
            for query in query_list:
                cache_key = self._generate_cache_key(query)
                # 缓存已禁用
                # await self.cache.set(cache_key, {...})

        # 为每个任务生成提示词
        results = {}
        for task in tasks:
            status = getattr(task, 'status', TaskStatus.TODO)
            if isinstance(status, str):
                status = TaskStatus(status)

            query = ContextQuery(
                task_id=task.id,
                task_title=task.title,
                task_description=getattr(task, 'description', None),
                input_data=getattr(task, 'input_data', {}),
                agent_id=getattr(task, 'assigned_agent', None) or getattr(task, 'assigned_agent_id', None),
                status=status,
            )

            cache_key = self._generate_cache_key(query)
            # 缓存已禁用：始终从 Grasp 查，确保数据一致性
            cached = None

            if cached:
                cognitions = cached["cognitions"]
                sections = cached.get("sections", self._group_by_section(cognitions, status))
            else:
                cognitions = []
                sections = {}

            results[task.id] = self._build_prompt_with_context(
                task, cognitions, sections, cache_hit=bool(cached), status=status
            )

        logger.info(
            f"Batch context injection: {len(tasks)} tasks, "
            f"{retrieval_time:.2f}ms, {len(cognitions_batch)} unique queries"
        )

        return results

    def get_stats(self) -> dict:
        """获取注入器统计"""
        cache_stats = self.cache.get_stats()
        avg_retrieval_time = (
            self._total_retrieval_time_ms / self._total_injections
            if self._total_injections > 0 else 0.0
        )

        return {
            "total_injections": self._total_injections,
            "cache_hits": self._cache_hits,
            "cache": cache_stats,
            "avg_retrieval_time_ms": avg_retrieval_time,
            "latency_check": "PASS" if avg_retrieval_time < 100 else "WARN",
            "hit_rate_check": "PASS" if cache_stats["hit_rate"] > 0.8 else "WARN",
        }

    async def invalidate_cache(self, task_id: str, new_status: TaskStatus):
        """
        任务状态变更时失效缓存 (SP2-17)

        注意：缓存已禁用，此方法现为 no-op。
        """
        logger.debug(f"Cache invalidation requested for task {task_id} -> {new_status.value} (cache disabled)")

    async def cleanup(self):
        """清理过期缓存（缓存已禁用，为 no-op）"""
        logger.debug("Context injector cleanup: cache disabled, no-op")

    async def refresh_cognition_version(self):
        """刷新认知版本号(用于缓存失效)"""
        self.grasp_adapter.get_cognition_version()
        logger.debug("Cognition version refreshed")

# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 枚举
    "TaskStatus",
    # 数据类
    "ContextTemplate",
    "CacheEntry",
    "ContextQuery",
    "ContextResult",
    "InjectionConfig",
    # 类
    "LRUCache",
    "GraspAdapter",
    "ContextInjector",
]
