"""
DispatchPoller — 异步派发结果轮询器（指数退避）

轮询异步平台（Dify/Coze）的 dispatch 结果，
指数退避：10s → 20s → 40s → 80s → 120s（cap）。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class PendingDispatch:
    """待轮询的派发任务"""
    task_id: str
    dispatch_id: str
    agent_id: str
    poll_interval: float = 10.0
    elapsed_seconds: float = 0.0
    timeout_seconds: int = 1800  # 30 分钟默认
    created_at: float = field(default_factory=time.time)


class DispatchPoller:
    """
    异步派发轮询器

    指数退避策略：
    - 初始间隔：10s
    - 最大间隔：120s
    - 乘数：2x
    - 默认超时：1800s（30 分钟）
    """

    INITIAL_POLL_INTERVAL = 10    # 秒
    MAX_POLL_INTERVAL = 120       # 秒
    BACKOFF_MULTIPLIER = 2        # 倍
    DEFAULT_TIMEOUT = 1800        # 秒

    def __init__(self, registry, agent_facade):
        self._registry = registry
        self._facade = agent_facade
        self._pending: dict[str, PendingDispatch] = {}
        self._running = False

    def add(self, dispatch: PendingDispatch):
        """添加一个待轮询的派发任务"""
        self._pending[dispatch.dispatch_id] = dispatch
        logger.info(
            f"[DispatchPoller] Added pending dispatch: task={dispatch.task_id} "
            f"dispatch={dispatch.dispatch_id}"
        )

    def remove(self, dispatch_id: str):
        """移除已完成/超时的派发任务"""
        if dispatch_id in self._pending:
            del self._pending[dispatch_id]

    async def poll_once(self, dispatch: PendingDispatch) -> bool:
        """
        单次轮询

        返回 True = 任务完成（成功或失败），应从 pending 移除
        返回 False = 继续轮询
        """
        now = time.time()
        dispatch.elapsed_seconds = now - dispatch.created_at

        # 检查超时
        timeout = dispatch.timeout_seconds or self.DEFAULT_TIMEOUT
        if dispatch.elapsed_seconds > timeout:
            logger.warning(
                f"[DispatchPoller] Dispatch {dispatch.dispatch_id} timed out "
                f"after {dispatch.elapsed_seconds:.0f}s"
            )
            await self._mark_failed(dispatch.task_id, "dispatch timeout")
            return True

        # 轮询结果
        result = await self._facade.get_result(dispatch.dispatch_id, dispatch.agent_id)
        if result:
            logger.info(
                f"[DispatchPoller] Dispatch {dispatch.dispatch_id} completed: "
                f"status={result.status}"
            )
            await self._complete_task(dispatch.task_id, result)
            return True

        # 未完成，继续轮询（更新间隔）
        dispatch.poll_interval = min(
            dispatch.poll_interval * self.BACKOFF_MULTIPLIER,
            self.MAX_POLL_INTERVAL,
        )
        return False

    async def run(self):
        """启动轮询循环"""
        self._running = True
        logger.info("[DispatchPoller] Poller started")

        while self._running:
            to_remove = []
            for dispatch_id, dispatch in list(self._pending.items()):
                if dispatch.elapsed_seconds >= dispatch.poll_interval:
                    done = await self.poll_once(dispatch)
                    if done:
                        to_remove.append(dispatch_id)
                else:
                    # 累计已等待时间
                    dispatch.elapsed_seconds += 1

            for dispatch_id in to_remove:
                self.remove(dispatch_id)

            await asyncio.sleep(1)

    def stop(self):
        """停止轮询器"""
        self._running = False
        logger.info("[DispatchPoller] Poller stopped")

    # ── Internal helpers ────────────────────────────────────────────────

    async def _mark_failed(self, task_id: str, reason: str):
        """标记任务失败"""
        await self._facade.complete_task(task_id, reason, success=False)

    async def _complete_task(self, task_id: str, result):
        """标记任务完成"""
        status = "done" if result.status == "success" else "failed"
        result_text = result.result or result.error or ""
        await self._facade.complete_task(task_id, result_text, success=(status == "done"))