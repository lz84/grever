"""Nexus 日志引擎 — 基于 Loguru"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

from .schema import LogEntry, Events

# 日志根目录: packages/server/logs/
_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'logs'
_LOG_DIR.mkdir(parents=True, exist_ok=True)

class LogEngine:
    """
    统一日志引擎 (单例)

    用法:
        LogEngine.init()                    # 启动时调用一次
        LogEngine.emit('scheduler', Events.TASK_ASSIGNED, {'task_id': 'xxx'})
        LogEngine.info('scheduler', 'Task started', task_id='xxx')
    """

    _initialized = False

    @classmethod
    def init(
        cls,
        log_dir: Optional[Path] = None,
        rotation: str = '50 MB',
        retention: str = '30 days',
        level: str = 'INFO',
        json_format: bool = True,
        trace_id_key: str = 'trace_id',
    ):
        """初始化 Loguru 日志引擎"""
        if cls._initialized:
            return

        log_dir = log_dir or _LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)

        # 移除默认 handler
        logger.remove()

        # 控制台 handler (人类可读)
        logger.add(
            sys.stderr,
            level=level,
            format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[module]: <12}</cyan> | <cyan>{extra[trace_id]: <10}</cyan> | {message}',
            enqueue=True,
        )

        # 结构化 JSON 文件 (机器可读)
        if json_format:
            json_log = log_dir / 'nexus-json.log'
            logger.add(
                str(json_log),
                level=level,
                rotation=rotation,
                retention=retention,
                serialize=True,
                enqueue=True,
                format='{message}',
            )

        # 按日期滚动的文本日志
        daily_log = log_dir / 'nexus_{time:YYYY-MM-DD}.log'
        logger.add(
            str(daily_log),
            level=level,
            rotation=rotation,
            retention=retention,
            enqueue=True,
            format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[module]: <12} | {extra[trace_id]: <10} | {message}',
        )

        # 错误日志单独存储
        error_log = log_dir / 'nexus-error.log'
        logger.add(
            str(error_log),
            level='ERROR',
            rotation=rotation,
            retention=retention,
            enqueue=True,
            format='{time:YYYY-MM-DD HH:mm:ss} | {extra[module]: <12} | {extra[trace_id]: <10} | {message}\n{exception}',
        )

        cls._initialized = True

    @classmethod
    def emit(
        cls,
        module: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        trace_id: str = '',
        level: str = 'info',
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """
        发射一条日志

        Args:
            module: 模块名 (scheduler/agent/execution/matching/...)
            event_type: 事件类型 (见 Events 类)
            payload: 结构化数据
            trace_id: 追踪 ID (留空则自动生成)
            level: 日志级别
            agent_id/task_id/project_id/goal_id: 关联实体
            metadata: 元数据 (duration_ms, llm_tokens 等)
        """
        entry = LogEntry(
            module=module,
            event_type=event_type,
            level=level,
            trace_id=trace_id,
            payload=payload or {},
            metadata=metadata or {},
            agent_id=agent_id,
            task_id=task_id,
            project_id=project_id,
            goal_id=goal_id,
        )

        # 绑定上下文
        ctx = logger.bind(
            module=module,
            trace_id=entry.trace_id,
            event_type=event_type,
        )
        if task_id:
            ctx = ctx.bind(task_id=task_id)
        if agent_id:
            ctx = ctx.bind(agent_id=agent_id)

        # 写入
        msg = f'[{event_type}] {cls._format_payload(payload)}'
        log_method = getattr(ctx, level, ctx.info)
        log_method(msg)

        return entry

    @classmethod
    def debug(cls, module: str, msg: str, **kwargs):
        logger.bind(module=module, trace_id=kwargs.pop('trace_id', '')).debug(msg)

    @classmethod
    def info(cls, module: str, msg: str, **kwargs):
        logger.bind(module=module, trace_id=kwargs.pop('trace_id', '')).info(msg)

    @classmethod
    def warning(cls, module: str, msg: str, **kwargs):
        logger.bind(module=module, trace_id=kwargs.pop('trace_id', '')).warning(msg)

    @classmethod
    def error(cls, module: str, msg: str, **kwargs):
        logger.bind(module=module, trace_id=kwargs.pop('trace_id', '')).error(msg)

    @classmethod
    def exception(cls, module: str, msg: str, **kwargs):
        logger.bind(module=module, trace_id=kwargs.pop('trace_id', '')).exception(msg)

    @staticmethod
    def _format_payload(payload: Optional[dict]) -> str:
        if not payload:
            return ''
        parts = []
        for k, v in payload.items():
            sv = str(v)
            if len(sv) > 100:
                sv = sv[:100] + '...'
            parts.append(f'{k}={sv}')
        return ' '.join(parts)

# 便捷函数 (模块级导入即可使用)
emit = LogEngine.emit
debug = LogEngine.debug
info = LogEngine.info
warning = LogEngine.warning
error = LogEngine.error
exception = LogEngine.exception
