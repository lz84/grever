"""Grever 日志查询模块"""
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# 日志存储目录
_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'logs'

class LogQuery:
    """
    日志查询器

    从 Loguru 的 JSON 日志文件中读取和过滤日志。
    Loguru serialize=True 输出每行一个 JSON 对象。
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or _LOG_DIR
        self.json_log = self.log_dir / 'grever-json.log'

    def query(
        self,
        module: Optional[str] = None,
        event_type: Optional[str] = None,
        level: Optional[str] = None,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询日志

        Args:
            module: 过滤模块
            event_type: 过滤事件类型
            level: 过滤级别 (debug/info/warn/error/critical)
            trace_id: 过滤追踪 ID
            task_id: 过滤任务 ID
            agent_id: 过滤 Agent ID
            limit: 返回条数
            offset: 偏移量

        Returns:
            日志条目列表 (每行一个 dict)
        """
        if not self.json_log.exists():
            return []

        results = []
        with open(self.json_log, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 过滤
                if module and entry.get('extra', {}).get('module') != module:
                    continue
                if event_type and entry.get('extra', {}).get('event_type') != event_type:
                    continue
                if level and entry.get('record', {}).get('level', {}).get('name', '').lower() != level.lower():
                    continue
                if trace_id and entry.get('extra', {}).get('trace_id') != trace_id:
                    continue
                if task_id and entry.get('extra', {}).get('task_id') != task_id:
                    continue
                if agent_id and entry.get('extra', {}).get('agent_id') != agent_id:
                    continue

                results.append(entry)

        # 分页
        results = results[offset:offset + limit]
        return results

    def query_by_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """按 trace_id 查询所有关联日志"""
        return self.query(trace_id=trace_id, limit=1000)

    def query_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """按 task_id 查询所有关联日志"""
        return self.query(task_id=task_id, limit=500)

    def query_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """查询最近的错误日志"""
        return self.query(level='error', limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        if not self.json_log.exists():
            return {'total_lines': 0, 'size_bytes': 0}

        total_lines = 0
        with open(self.json_log, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    total_lines += 1

        return {
            'total_lines': total_lines,
            'size_bytes': self.json_log.stat().st_size,
            'file_path': str(self.json_log),
        }
