"""
执行编排器 — ProjectExecutor 主类

职责：
1. 管理单个项目的任务执行流程
2. poll in_progress 池，收集完成的
3. 找新的 ready 任务
4. 触发新任务
5. 判断是否完成
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import Table, MetaData, or_
from sqlalchemy.orm import aliased
from models.task import Task
from models.project import Project
from models.agent import Agent

from .dispatch_coordinator import mark_in_progress, log_activity, log_execution
from .result_collector import collect_result, get_goal_id


class ProjectExecutor:
    """单项目执行器 — 管理项目内所有任务的执行"""

    def __init__(self, project_id: str, db_manager, nexus_url: str = ""):
        self.project_id = project_id
        self.db = db_manager
        self.nexus_url = nexus_url
        self.in_progress: Dict[str, Any] = {}
        self.state = "running"
        logger.info(f"[ProjectExecutor] Initialized for project {project_id}")

    async def tick(self) -> Dict[str, Any]:
        """
        执行一次调度循环：
        0. 恢复孤儿任务
        1. poll in_progress 池
        2. 处理完成的
        3. 找新的 ready 任务
        4. 触发新任务
        5. 判断是否完成
        """
        results = []
        logger.info(f"[ProjectExecutor.tick] START project={self.project_id}", flush=True)

        # 0. 恢复孤儿任务
        orphan_ids = await self._recover_orphaned_tasks()

        # 1. poll 已启动的任务
        from .task_runner_compat import check_completed
        completed_ids = []
        for task_id, process in self.in_progress.items():
            if check_completed(process):
                completed_ids.append(task_id)

        if completed_ids:
            logger.info(
                f"[ProjectExecutor] Found {len(completed_ids)} completed tasks in project {self.project_id}"
            )

        # 2. 处理完成的
        for task_id in completed_ids:
            try:
                result = await collect_result(self.db, self.project_id, task_id, self.in_progress)
                results.append(result)
            except Exception as e:
                logger.error(f"[ProjectExecutor] collect_result failed for {task_id}: {e}")
                results.append({"task_id": task_id, "success": False})
            finally:
                if task_id in self.in_progress:
                    del self.in_progress[task_id]

        # 3. 找新的 ready 任务
        ready_tasks = await self._find_ready_tasks()

        # 当所有任务都完成时触发 auto_capture_solution
        if completed_ids and not self.in_progress and not ready_tasks:
            goal_id = get_goal_id(self.db, self.project_id)
            if goal_id:
                try:
                    from grasp.api.solutions import auto_capture_solution
                    with self.db.engine.connect() as conn:
                        class _DbWrapper:
                            def __init__(self, c):
                                self._conn = c
                            def execute(self, query, params=None):
                                return self._conn.execute(query, params or {})
                            def commit(self):
                                self._conn.commit()
                        db_wrap = _DbWrapper(conn)
                        sol = auto_capture_solution(goal_id, db_wrap)
                        if sol:
                            logger.info(
                                f"[ProjectExecutor] Auto-captured solution {sol.get('id')} for goal {goal_id}"
                            )
                except Exception as e:
                    logger.error(f"[ProjectExecutor] auto_capture_solution error: {e}")

        # 4. 触发新任务
        launched_count = 0
        for task in ready_tasks:
            try:
                task_id = task.get("id", "?")
                agent_id = task.get("assigned_agent")
                agent_name = task.get("agent_name", "main")
                logger.info(
                    f"[ProjectExecutor] About to launch task {task_id}: agent_name={agent_name}, agent_id={agent_id}",
                    flush=True,
                )
                if not agent_id:
                    logger.error(
                        f"[ProjectExecutor] Task {task_id} has no assigned_agent — "
                        f"agent assignment is creation-time responsibility"
                    )
                    continue

                from .task_runner_compat import launch
                process = await launch(task, agent_id, self.nexus_url, db=self.db)
                self.in_progress[task["id"]] = process
                launched_count += 1

                mark_in_progress(self.db, task["id"], agent_id)

                log_activity(
                    self.db, task["id"], "todo", "in_progress",
                    reason=f"任务开始执行，agent={agent_id}", actor="system",
                )
                log_execution(
                    db=self.db,
                    task_id=task["id"],
                    agent_id=agent_id,
                    action="task_start",
                    input_data={
                        "task_title": task.get("title", ""),
                        "task_description": task.get("description", ""),
                        "agent_id": agent_id,
                    },
                    output_data={},
                    status="success",
                )
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"[ProjectExecutor] Failed to launch task {task.get('id')}: {e}\n{tb}")

        # 5. 判断是否完成
        if not self.in_progress and not ready_tasks:
            self.state = "completed"
            logger.info(f"[ProjectExecutor] Project {self.project_id} completed")

        return {"completed": results, "launched": launched_count}

    async def _recover_orphaned_tasks(self) -> List[str]:
        """恢复孤儿任务 — DB 中 in_progress 但内存池没有的"""
        recovered = []
        try:
            session = self.db.get_session()
            try:
                orphan_tasks = (
                    session.query(Task)
                    .filter(Task.project_id == self.project_id, Task.status == 'in_progress')
                    .all()
                )
            finally:
                session.close()

            for task in orphan_tasks:
                task_id = task.id
                if task_id in self.in_progress:
                    continue
                from .task_runner_compat import read_result
                result_data = await read_result(task_id)
                if result_data:
                    logger.info(f"[ProjectExecutor] Orphan task {task_id}: result file found")
                    result = await collect_result(self.db, self.project_id, task_id, self.in_progress)
                    recovered.append(task_id)
                else:
                    logger.info(f"[ProjectExecutor] Orphan task {task_id}: no result file, leaving for recoverer")
        except Exception as e:
            logger.error(f"[ProjectExecutor] _recover_orphaned_tasks error: {e}")
        return recovered

    async def _find_ready_tasks(self) -> List[Dict[str, Any]]:
        """找新的 ready 任务（已分配 agent），只返回已分配 agent 的任务"""
        try:
            from reins.common.database import get_db_session
            session = get_db_session()
            try:
                AgentAlias = aliased(Agent, name='agent')
                tasks = (
                    session.query(Task, AgentAlias.name.label('agent_name'))
                    .outerjoin(AgentAlias, Task.assigned_agent == AgentAlias.id)
                    .filter(
                        Task.project_id == self.project_id,
                        Task.status == 'todo',
                        Task.assigned_agent.isnot(None),
                    )
                    .order_by(Task.created_at.asc())
                    .all()
                )

                result = []
                for task, agent_name in tasks:
                    agent_name = agent_name or "main"
                    result.append({
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "project_id": task.project_id,
                        "assigned_agent": task.assigned_agent,
                        "agent_name": agent_name,
                        "status": task.status,
                        "acceptance_criteria": task.acceptance_criteria,
                        "verifier_agent_id": task.verifier_agent_id,
                        "created_at": task.created_at,
                    })

                logger.info(f"[ProjectExecutor] Found {len(result)} ready tasks for project {self.project_id}", flush=True)
                return result
            finally:
                session.close()
        except Exception as e:
            logger.error(f"[ProjectExecutor] Failed to find ready tasks for project {self.project_id}: {e}")
            return []

    def is_completed(self) -> bool:
        """判断项目是否完成"""
        return self.state == "completed"

    def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            "project_id": self.project_id,
            "state": self.state,
            "in_progress": len(self.in_progress),
        }


def _get_constraint_text(session, project_id: str) -> str:
    """获取当前轮次约束文本，注入到任务描述中"""
    try:
        project = session.query(Project.goal_id).filter(Project.id == project_id).first()
        if not project:
            return ""
        goal_id = project.goal_id

        meta = MetaData()
        constraints_tbl = Table("iteration_constraints", meta, autoload_with=session.bind)
        stmt = (
            constraints_tbl.select()
            .where(constraints_tbl.c.goal_id == goal_id)
            .order_by(constraints_tbl.c.round.desc())
            .limit(1)
        )
        cons_row = session.execute(stmt).fetchone()
        if not cons_row or not cons_row[0]:
            return ""

        constraints = json.loads(cons_row[0])
        if not constraints or not isinstance(constraints, dict):
            return ""

        parts = []
        for key, value in constraints.items():
            key_lower = key.lower()
            num = None
            if isinstance(value, (int, float)):
                num = value
            elif isinstance(value, str):
                import re
                match = re.search(r"[-+]?\d*\.?\d+", value)
                if match:
                    num = float(match.group())

            if num is not None:
                if "duration" in key_lower or "工期" in key or "time" in key_lower:
                    parts.append(f"工期≤{num}天")
                elif "cost" in key_lower or "成本" in key or "费用" in key or "price" in key_lower:
                    cost_wan = num / 10000 if num >= 10000 else num
                    unit = "万" if num >= 10000 else "元"
                    parts.append(f"成本≤{cost_wan}{unit}")
                elif "safety" in key_lower or "安全" in key or "quality" in key_lower:
                    parts.append(f"安全系数≥{num}")
                else:
                    parts.append(f"{key}={num}")
            elif isinstance(value, str) and value.strip():
                parts.append(f"{value}")

        return "，".join(parts) if parts else ""
    except Exception as e:
        logger.warning(f"[ProjectExecutor] Failed to get constraint text: {e}")
        return ""
