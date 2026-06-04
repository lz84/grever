# -*- coding: utf-8 -*-
"""
单元测试: reins/logging/ 模块

覆盖:
1. LogEntry - 数据类创建、序列化
2. Events - 事件常量
3. LogQuery - 日志查询
4. LogEngine - 日志引擎基本功能
"""

import pytest
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from shared.logging.schema import LogEntry, Events
from shared.logging.queries import LogQuery


# ============================================================================
# LogEntry Tests
# ============================================================================

class TestLogEntry:
    """LogEntry 数据类测试"""

    def test_log_entry_auto_fields(self):
        """测试自动生成的 id, timestamp, trace_id"""
        entry = LogEntry(module='scheduler', event_type=Events.TASK_ASSIGNED)
        assert entry.id.startswith('log-')
        assert len(entry.id) > 4
        assert entry.timestamp
        assert entry.trace_id.startswith('trace-')
        assert entry.level == 'info'

    def test_log_entry_custom_fields(self):
        """测试自定义字段"""
        entry = LogEntry(
            module='agent',
            event_type=Events.AGENT_HEARTBEAT,
            level='debug',
            trace_id='custom-trace-123',
            agent_id='agent-001',
            task_id='task-001',
            project_id='proj-001',
            goal_id='goal-001',
            payload={'key': 'value'},
            metadata={'duration_ms': 100},
        )
        assert entry.level == 'debug'
        assert entry.trace_id == 'custom-trace-123'
        assert entry.agent_id == 'agent-001'
        assert entry.task_id == 'task-001'
        assert entry.payload == {'key': 'value'}
        assert entry.metadata == {'duration_ms': 100}

    def test_log_entry_to_dict(self):
        """测试 to_dict 序列化"""
        entry = LogEntry(
            module='execution',
            event_type=Events.EXECUTION_STARTED,
            payload={'task': 't1'},
        )
        d = entry.to_dict()
        assert d['module'] == 'execution'
        assert d['event_type'] == Events.EXECUTION_STARTED
        assert d['payload'] == {'task': 't1'}
        assert d['id'] == entry.id

    def test_log_entry_to_json_line(self):
        """测试 to_json_line 输出"""
        entry = LogEntry(
            module='matching',
            event_type=Events.MATCH_SUCCESS,
        )
        json_line = entry.to_json_line()
        parsed = json.loads(json_line)
        assert parsed['module'] == 'matching'
        assert parsed['event_type'] == Events.MATCH_SUCCESS


# ============================================================================
# Events Tests
# ============================================================================

class TestEvents:
    """Events 常量测试"""

    def test_scheduler_events(self):
        """测试 Scheduler 事件"""
        assert Events.TASK_ASSIGNED == 'task_assigned'
        assert Events.TASK_COMPLETED == 'task_completed'
        assert Events.TASK_FAILED == 'task_failed'
        assert Events.TASK_TIMEOUT == 'task_timeout'
        assert Events.TASK_RECOVERED == 'task_recovered'
        assert Events.DEPENDENCY_UNLOCKED == 'dependency_unlocked'

    def test_agent_events(self):
        """测试 Agent 事件"""
        assert Events.AGENT_HEARTBEAT == 'agent_heartbeat'
        assert Events.AGENT_ONLINE == 'agent_online'
        assert Events.AGENT_OFFLINE == 'agent_offline'
        assert Events.AGENT_STALE == 'agent_stale'

    def test_verification_events(self):
        """测试 Verification 事件"""
        assert Events.VERIFICATION_STARTED == 'verification_started'
        assert Events.VERIFICATION_PASSED == 'verification_passed'
        assert Events.VERIFICATION_FAILED == 'verification_failed'
        assert Events.VERIFICATION_DISPUTED == 'verification_disputed'

    def test_goal_project_events(self):
        """测试 Goal/Project 事件"""
        assert Events.GOAL_DECOMPOSED == 'goal_decomposed'
        assert Events.PROJECT_COMPLETED == 'project_completed'
        assert Events.GOAL_COMPLETED == 'goal_completed'

    def test_command_bus_events(self):
        """测试 Command Bus 事件"""
        assert Events.COMMAND_DISPATCHED == 'command_dispatched'
        assert Events.COMMAND_FAILED == 'command_failed'


# ============================================================================
# LogQuery Tests
# ============================================================================

class TestLogQuery:
    """LogQuery 日志查询器测试"""

    def test_query_no_log_file(self, tmp_path):
        """测试日志文件不存在时返回空列表"""
        query = LogQuery(log_dir=tmp_path)
        result = query.query()
        assert result == []

    def test_get_stats_no_log_file(self, tmp_path):
        """测试无日志文件时的统计"""
        query = LogQuery(log_dir=tmp_path)
        stats = query.get_stats()
        assert stats['total_lines'] == 0
        assert stats['size_bytes'] == 0

    def test_query_with_log_file(self, tmp_path):
        """测试从 JSON 日志文件查询"""
        # 写入测试日志
        log_file = tmp_path / 'nexus-json.log'
        entries = [
            json.dumps({
                'extra': {'module': 'scheduler', 'event_type': 'task_assigned', 'trace_id': 't1'},
                'record': {'level': {'name': 'info'}},
            }),
            json.dumps({
                'extra': {'module': 'agent', 'event_type': 'agent_heartbeat', 'trace_id': 't2'},
                'record': {'level': {'name': 'error'}},
            }),
            json.dumps({
                'extra': {'module': 'scheduler', 'event_type': 'task_completed', 'trace_id': 't1'},
                'record': {'level': {'name': 'info'}},
            }),
        ]
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(entries) + '\n')

        query = LogQuery(log_dir=tmp_path)

        # 查全部
        all_results = query.query()
        assert len(all_results) == 3

        # 按模块过滤
        scheduler_results = query.query(module='scheduler')
        assert len(scheduler_results) == 2

        # 按事件类型过滤
        heartbeat_results = query.query(event_type='agent_heartbeat')
        assert len(heartbeat_results) == 1

        # 按级别过滤
        error_results = query.query(level='error')
        assert len(error_results) == 1

        # 按 trace_id 过滤
        trace_results = query.query(trace_id='t1')
        assert len(trace_results) == 2

    def test_query_pagination(self, tmp_path):
        """测试分页查询"""
        log_file = tmp_path / 'nexus-json.log'
        entries = []
        for i in range(10):
            entries.append(json.dumps({
                'extra': {'module': 'test', 'event_type': f'event_{i}', 'trace_id': f't{i}'},
                'record': {'level': {'name': 'info'}},
            }))
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(entries) + '\n')

        query = LogQuery(log_dir=tmp_path)
        page1 = query.query(limit=3, offset=0)
        assert len(page1) == 3

        page2 = query.query(limit=3, offset=3)
        assert len(page2) == 3

    def test_query_by_trace(self, tmp_path):
        """测试按 trace_id 查询"""
        log_file = tmp_path / 'nexus-json.log'
        entries = [
            json.dumps({'extra': {'module': 'test', 'event_type': 'e1', 'trace_id': 'my-trace'}, 'record': {'level': {'name': 'info'}}}),
            json.dumps({'extra': {'module': 'test', 'event_type': 'e2', 'trace_id': 'my-trace'}, 'record': {'level': {'name': 'info'}}}),
            json.dumps({'extra': {'module': 'test', 'event_type': 'e3', 'trace_id': 'other'}, 'record': {'level': {'name': 'info'}}}),
        ]
        with open(log_file, 'w') as f:
            f.write('\n'.join(entries) + '\n')

        query = LogQuery(log_dir=tmp_path)
        results = query.query_by_trace('my-trace')
        assert len(results) == 2

    def test_query_errors(self, tmp_path):
        """测试错误日志查询"""
        log_file = tmp_path / 'nexus-json.log'
        entries = [
            json.dumps({'extra': {'module': 'test', 'event_type': 'e1', 'trace_id': 't1'}, 'record': {'level': {'name': 'info'}}}),
            json.dumps({'extra': {'module': 'test', 'event_type': 'e2', 'trace_id': 't2'}, 'record': {'level': {'name': 'error'}}}),
        ]
        with open(log_file, 'w') as f:
            f.write('\n'.join(entries) + '\n')

        query = LogQuery(log_dir=tmp_path)
        errors = query.query_errors()
        assert len(errors) == 1
        assert errors[0]['record']['level']['name'] == 'error'

    def test_query_malformed_lines(self, tmp_path):
        """测试处理格式错误的日志行"""
        log_file = tmp_path / 'nexus-json.log'
        with open(log_file, 'w') as f:
            f.write('not valid json\n')
            f.write('{"extra": {"module": "test", "event_type": "e1", "trace_id": "t1"}, "record": {"level": {"name": "info"}}}\n')
            f.write('\n')  # 空行

        query = LogQuery(log_dir=tmp_path)
        results = query.query()
        assert len(results) == 1

    def test_get_stats_with_file(self, tmp_path):
        """测试有日志文件时的统计"""
        log_file = tmp_path / 'nexus-json.log'
        with open(log_file, 'w') as f:
            f.write('{"extra": {}, "record": {}}\n')
            f.write('{"extra": {}, "record": {}}\n')

        query = LogQuery(log_dir=tmp_path)
        stats = query.get_stats()
        assert stats['total_lines'] == 2
        assert stats['size_bytes'] > 0
