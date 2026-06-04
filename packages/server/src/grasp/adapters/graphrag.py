"""
GraphRAGAdapter — Microsoft GraphRAG 后端适配器（Phase 1b）

使用 subprocess 调用 graphrag CLI：
  python -m graphrag.index --root {root}    # 构建索引
  python -m graphrag.query  --root {root} --query "{query}" --method {local|global}

支持：
  - 批量窗口：inject 后延迟 build_index，攒多条一起索引
  - 每日成本上限：配置 max_daily_cost_usd
  - 小内容跳过：< 500 字直接转发给 MemoryAdapter
  - 自动降级：GraphRAG 不可用时自动切换到 memory 后端
"""

import asyncio
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

from grasp.adapters.base import BaseGraspAdapter
from grasp.facade.models import (
    CognitionInput, InjectResult, RetrieveResult, UpdateResult, CognitionItem
)

logger = logging.getLogger(__name__)


# ============================================================
# 配置
# ============================================================

DEFAULT_GRAPHRAG_ROOT = str(Path(__file__).resolve().parents[5] / "data" / "graphrag")
DEFAULT_BATCH_WINDOW_SEC = 60
DEFAULT_MAX_DAILY_COST_USD = 10.0
DEFAULT_SMALL_CONTENT_THRESHOLD = 500
CLI_TIMEOUT_SEC = 300


# ============================================================
# 成本控制模块
# ============================================================

class CostController:
    """
    成本控制器：
    1. 每日成本上限（max_daily_cost_usd）
    2. 批量窗口（batch_window_sec）
    3. 小内容跳过（small_content_threshold）
    """

    def __init__(
        self,
        max_daily_cost_usd: float = DEFAULT_MAX_DAILY_COST_USD,
        batch_window_sec: int = DEFAULT_BATCH_WINDOW_SEC,
        small_content_threshold: int = DEFAULT_SMALL_CONTENT_THRESHOLD,
    ):
        self.max_daily_cost_usd = max_daily_cost_usd
        self.batch_window_sec = batch_window_sec
        self.small_content_threshold = small_content_threshold

        # 每日成本追踪
        self._daily_cost: Dict[str, float] = {}  # date_str -> cost
        self._cost_lock = threading.Lock()

        # 批量队列
        self._pending_docs: List[Dict[str, str]] = []  # [{doc_id, content}]
        self._pending_lock = threading.Lock()
        self._last_build_time: Optional[datetime] = None
        self._batch_timer_task: Optional[asyncio.Task] = None

    def is_small_content(self, content: str) -> bool:
        """内容是否小于阈值（不走 GraphRAG）"""
        return len(content) < self.small_content_threshold

    def check_cost_limit(self) -> bool:
        """检查是否超过每日成本上限"""
        today = date.today().isoformat()
        with self._cost_lock:
            cost = self._daily_cost.get(today, 0.0)
            return cost < self.max_daily_cost_usd

    def record_cost(self, cost_usd: float):
        """记录一次 LLM 调用的成本"""
        today = date.today().isoformat()
        with self._cost_lock:
            self._daily_cost[today] = self._daily_cost.get(today, 0.0) + cost_usd
            logger.debug(f"[CostController] 今日成本: {self._daily_cost[today]:.4f} USD")

    def add_pending_doc(self, doc_id: str, content: str):
        """添加待索引文档到批量队列"""
        with self._pending_lock:
            self._pending_docs.append({"doc_id": doc_id, "content": content})
            logger.debug(f"[CostController] pending size={len(self._pending_docs)}")

    def get_pending_count(self) -> int:
        with self._pending_lock:
            return len(self._pending_docs)

    def flush_pending(self) -> List[Dict[str, str]]:
        """弹出所有待索引文档"""
        with self._pending_lock:
            docs = self._pending_docs.copy()
            self._pending_docs.clear()
            return docs


# ============================================================
# 降级/健康检查模块
# ============================================================

class HealthChecker:
    """
    健康检查 + 自动降级：
    1. 每 60 秒检查 GraphRAG CLI 可用性
    2. GraphRAG 不可用时通知 Facade 切换到 memory
    3. GraphRAG 恢复后自动切回
    """

    def __init__(
        self,
        check_interval_sec: int = 60,
        graphrag_root: str = DEFAULT_GRAPHRAG_ROOT,
    ):
        self.check_interval_sec = check_interval_sec
        self.graphrag_root = graphrag_root
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._fallback_handler: Optional[callable] = None

        # 状态追踪
        self._graphrag_available: bool = False
        self._last_check_time: Optional[datetime] = None
        self._consecutive_failures: int = 0

    def set_fallback_handler(self, handler: callable):
        """设置降级回调：接收 (available: bool) 参数"""
        self._fallback_handler = handler

    async def start(self):
        """启动健康检查循环"""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("[HealthChecker] 健康检查循环已启动")

    async def stop(self):
        """停止健康检查"""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[HealthChecker] 健康检查循环已停止")

    def is_graphrag_available(self) -> bool:
        return self._graphrag_available

    async def _check_loop(self):
        """健康检查循环"""
        while self._is_running:
            try:
                await asyncio.sleep(self.check_interval_sec)
                await self._do_check()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"[HealthChecker] 检查异常: {e}")

    async def _do_check(self):
        """执行一次健康检查"""
        available = await self._check_cli()
        now = datetime.now()

        if available:
            self._consecutive_failures = 0
            if not self._graphrag_available:
                logger.info("[HealthChecker] GraphRAG 恢复可用，通知切换")
                self._graphrag_available = True
                if self._fallback_handler:
                    try:
                        self._fallback_handler(True)
                    except Exception as e:
                        logger.warning(f"[HealthChecker] 恢复回调异常: {e}")
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                logger.warning(f"[HealthChecker] GraphRAG 连续 {self._consecutive_failures} 次检查失败，降级")
                self._graphrag_available = False
                if self._fallback_handler:
                    try:
                        self._fallback_handler(False)
                    except Exception as e:
                        logger.warning(f"[HealthChecker] 降级回调异常: {e}")

        self._last_check_time = now

    async def _check_cli(self) -> bool:
        """检查 graphrag CLI 是否可用"""
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "graphrag", "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except Exception as e:
            logger.debug(f"[HealthChecker] CLI 检查失败: {e}")
            return False


# ============================================================
# GraphRAGAdapter
# ============================================================

class GraphRAGAdapter(BaseGraspAdapter):
    """
    Microsoft GraphRAG 后端适配器

    通过 subprocess 调用 CLI，不直接依赖 graphrag Python 包。
    """

    def __init__(
        self,
        graphrag_root: str = DEFAULT_GRAPHRAG_ROOT,
        max_daily_cost_usd: float = DEFAULT_MAX_DAILY_COST_USD,
        batch_window_sec: int = DEFAULT_BATCH_WINDOW_SEC,
        small_content_threshold: int = DEFAULT_SMALL_CONTENT_THRESHOLD,
    ):
        self.graphrag_root = Path(graphrag_root)
        self.input_dir = self.graphrag_root / "input"

        # 确保输入目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)

        # 成本控制器
        self.cost_controller = CostController(
            max_daily_cost_usd=max_daily_cost_usd,
            batch_window_sec=batch_window_sec,
            small_content_threshold=small_content_threshold,
        )

        # 健康检查器
        self.health_checker = HealthChecker(
            graphrag_root=str(self.graphrag_root),
        )

        # 存储映射：cognition_id -> (content_hash, created_at)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._hash_index: Dict[str, str] = {}

        # Facade 引用（用于降级回调）
        self._facade_ref: Optional[Any] = None

    @property
    def name(self) -> str:
        return "microsoft-graphrag"

    def set_facade(self, facade):
        """注入 Facade 引用（用于 switch_backend）"""
        self._facade_ref = facade

    # ----- BaseGraspAdapter 实现 -----

    def is_available(self) -> bool:
        """检查 GraphRAG CLI 是否可用"""
        try:
            import subprocess as _sp
            import sys as _sys
            cmd = [_sys.executable, "-m", "graphrag", "--help"]
            result = _sp.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as _e:
            import logging
            logging.error(f"[GraphRAGAdapter] is_available exception: {_e}")
            return False

    def is_async_native(self) -> bool:
        return True

    def is_session_based(self) -> bool:
        return False

    def validate_filters(self, filters: Dict[str, Any]) -> List[str]:
        """GraphRAG 支持的 filters: type, tags, domain, min_confidence"""
        unsupported = []
        supported = {"type", "tags", "domain", "min_confidence", "mode"}
        for key in filters:
            if key not in supported:
                unsupported.append(key)
        return unsupported

    async def inject(self, cognition: CognitionInput) -> InjectResult:
        """
        注入认知：
        1. 小内容跳过 → 转发给 MemoryAdapter
        2. 成本上限检查 → 超出返回错误
        3. 写入临时输入文件，加入批量队列
        4. 触发批量窗口计时
        """
        # 1. 小内容跳过 → 转发给 MemoryAdapter
        if self.cost_controller.is_small_content(cognition.content):
            logger.debug(f"[GraphRAGAdapter] 内容过小（{len(cognition.content)} < {self.cost_controller.small_content_threshold}），转发给 MemoryAdapter")
            return await self._delegate_to_memory(cognition)

        # 2. 成本检查
        if not self.cost_controller.check_cost_limit():
            raise RuntimeError(
                f"GraphRAG 每日成本上限已达（${self.cost_controller.max_daily_cost_usd}），"
                "inject 被拒绝"
            )

        cognition_id = f"cog-{uuid.uuid4().hex[:12]}"
        content_hash = hashlib.sha256(
            cognition.content.encode('utf-8')
        ).hexdigest()[:16]

        # 3. 幂等检查
        if content_hash in self._hash_index:
            existing_id = self._hash_index[content_hash]
            return InjectResult(
                cognition_id=existing_id,
                backend=self.name,
                quality_score=0.0,
                is_duplicate=True,
            )

        # 4. 写入输入文件
        file_path = self.input_dir / f"{cognition_id}.txt"
        doc_content = self._make_document(cognition)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_content)

        # 5. 记录存储
        self._store[cognition_id] = {
            "content": cognition.content,
            "type": cognition.type,
            "tags": list(cognition.tags),
            "confidence": cognition.confidence,
            "metadata": dict(cognition.metadata or {}),
            "domain": cognition.domain,
            "_content_hash": content_hash,
            "_created_at": datetime.now().isoformat(),
        }
        self._hash_index[content_hash] = cognition_id

        # 6. 加入批量队列
        self.cost_controller.add_pending_doc(cognition_id, cognition.content)

        # 7. 触发批量窗口计时（如果尚未启动）
        await self._ensure_batch_timer()

        # 8. 记录成本（GraphRAG 每次索引约 $0.01 估算）
        self.cost_controller.record_cost(0.01)

        return InjectResult(
            cognition_id=cognition_id,
            backend=self.name,
            quality_score=0.0,
            is_duplicate=False,
        )

    async def retrieve(
        self,
        query: str,
        mode: str = "local",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RetrieveResult:
        """检索认知 — 调用 graphrag query CLI"""
        filters = filters or {}

        # 调用 CLI
        cmd = [
            sys.executable, "-m", "graphrag", "query",
            "--root", str(self.graphrag_root),
            query,
        ]
        if mode == "global":
            cmd.append("--method")
            cmd.append("global")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=CLI_TIMEOUT_SEC
            )
        except asyncio.TimeoutError:
            logger.error("[GraphRAGAdapter] query 超时")
            return RetrieveResult(items=[], total=0, has_more=False)
        except Exception as e:
            logger.error(f"[GraphRAGAdapter] query 异常: {e}")
            return RetrieveResult(items=[], total=0, has_more=False)

        if proc.returncode != 0:
            logger.warning(f"[GraphRAGAdapter] query 非零返回: {stderr.decode()}")
            return RetrieveResult(items=[], total=0, has_more=False)

        output = stdout.decode("utf-8", errors="replace")
        items = self._parse_query_output(output, limit, filters)

        return RetrieveResult(
            items=items,
            total=len(items),
            has_more=limit < len(items),
        )

    async def update(
        self, cognition_id: str, content: str,
        metadata: Dict[str, Any]
    ) -> UpdateResult:
        """更新认知 — 重新写入并触发重建"""
        if cognition_id not in self._store:
            raise KeyError(f"Cognition '{cognition_id}' not found")

        entry = self._store[cognition_id]
        old_hash = entry["_content_hash"]

        # 更新内容
        entry["content"] = content
        entry["metadata"] = dict(metadata or {})

        # 更新 hash 索引
        new_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        entry["_content_hash"] = new_hash
        del self._hash_index[old_hash]
        self._hash_index[new_hash] = cognition_id

        # 重新写入文件
        doc_content = self._make_doc_from_content(content, entry)
        file_path = self.input_dir / f"{cognition_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_content)

        return UpdateResult(
            cognition_id=cognition_id,
            quality_score=0.0,
        )

    async def delete(self, cognition_id: str) -> bool:
        """删除认知"""
        if cognition_id not in self._store:
            return False

        entry = self._store.pop(cognition_id)
        content_hash = entry["_content_hash"]
        if content_hash in self._hash_index:
            del self._hash_index[content_hash]

        file_path = self.input_dir / f"{cognition_id}.txt"
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass

        return True

    async def search_by_content_hash(
        self, content_hash: str, domain: Optional[str] = None
    ) -> Optional[CognitionInput]:
        """根据 content hash 查重"""
        if content_hash not in self._hash_index:
            return None
        cognition_id = self._hash_index[content_hash]
        entry = self._store.get(cognition_id)
        if entry is None:
            return None
        if domain and entry.get("domain") != domain:
            return None

        cog = CognitionInput(
            content=entry["content"],
            type=entry["type"],
            tags=entry["tags"],
            confidence=entry["confidence"],
            metadata=entry["metadata"],
            domain=entry.get("domain"),
        )
        cog._cognition_id = cognition_id
        return cog

    def get_status(self) -> Dict[str, Any]:
        """返回后端状态"""
        return {
            "index_size": len(self._store),
            "backend_version": "1.0.0",
            "pending_count": self.cost_controller.get_pending_count(),
            "graphrag_root": str(self.graphrag_root),
        }

    # ----- 内部方法 -----

    async def _delegate_to_memory(self, cognition: CognitionInput) -> InjectResult:
        """小内容跳过时，转发给 MemoryAdapter 处理"""
        from grasp.adapters.memory import MemoryAdapter
        memory_adapter = MemoryAdapter()
        return await memory_adapter.inject(cognition)

    def _make_document(self, cognition: CognitionInput) -> str:
        """将 CognitionInput 转换为 GraphRAG 输入文档"""
        lines = [
            f"# Cognition: {cognition.content[:80]}",
            f"type: {cognition.type}",
            f"tags: {', '.join(cognition.tags)}",
            f"domain: {cognition.domain or ''}",
            f"confidence: {cognition.confidence}",
            "",
            cognition.content,
        ]
        return "\n".join(lines)

    def _make_doc_from_content(self, content: str, entry: Dict) -> str:
        lines = [
            f"# Cognition: {content[:80]}",
            f"type: {entry.get('type', 'what')}",
            f"tags: {', '.join(entry.get('tags', []))}",
            f"domain: {entry.get('domain', '')}",
            f"confidence: {entry.get('confidence', 0.8)}",
            "",
            content,
        ]
        return "\n".join(lines)

    def _parse_query_output(
        self, output: str, limit: int, filters: Dict
    ) -> List[CognitionItem]:
        """
        解析 graphrag query 的输出。
        尝试从输出中提取文本块作为检索结果。
        """
        items = []

        # GraphRAG query 输出格式：Markdown 或纯文本
        # 简单策略：按行分割，提取非空段落作为 content
        # 在实际使用中，GraphRAG 输出结构化结果，这里做简化处理
        paragraphs = []
        current = []
        for line in output.splitlines():
            line = line.strip()
            if line:
                current.append(line)
            else:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
        if current:
            paragraphs.append(" ".join(current))

        # 类型过滤
        filter_type = filters.get("type")
        if filter_type:
            if isinstance(filter_type, list):
                filter_types = filter_type
            else:
                filter_types = [filter_type]

        for i, text in enumerate(paragraphs[:limit]):
            cog_type = "what"
            if filter_type:
                if isinstance(filter_type, list):
                    cog_type = filter_type[0]
                else:
                    cog_type = filter_type

            items.append(CognitionItem(
                cognition_id=f"cog-result-{i}",
                type=cog_type,
                content=text,
                tags=[],
                confidence=0.8,
                quality_score=0.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ))

        return items

    async def _ensure_batch_timer(self):
        """确保批量窗口计时器已启动"""
        # 如果有待处理的文档且计时器未启动，则启动
        if self.cost_controller.get_pending_count() > 0:
            if self.cost_controller._batch_timer_task is None or \
               self.cost_controller._batch_timer_task.done():
                self.cost_controller._batch_timer_task = asyncio.create_task(
                    self._batch_timerCoroutine()
                )

    async def _batch_timerCoroutine(self):
        """批量窗口计时协程：等待窗口后触发 build_index"""
        try:
            await asyncio.sleep(self.cost_controller.batch_window_sec)
            await self._flush_build_index()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[GraphRAGAdapter] 批量索引异常: {e}")

    async def _flush_build_index(self):
        """执行批量索引（调用 graphrag index CLI）"""
        docs = self.cost_controller.flush_pending()
        if not docs:
            return

        logger.info(f"[GraphRAGAdapter] 批量构建索引: {len(docs)} 条")

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "graphrag", "index",
                "--root", str(self.graphrag_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=CLI_TIMEOUT_SEC
            )
            if proc.returncode != 0:
                logger.error(f"[GraphRAGAdapter] index 失败: {stderr.decode()}")
            else:
                logger.info(f"[GraphRAGAdapter] index 完成")
        except asyncio.TimeoutError:
            logger.error("[GraphRAGAdapter] index 超时")
        except Exception as e:
            logger.error(f"[GraphRAGAdapter] index 异常: {e}")