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
from sqlalchemy import text

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
            with self.db.engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT id FROM tasks WHERE project_id = :pid AND status = 'in_progress'"),
                    {"pid": self.project_id},
                ).fetchall()

            for row in rows:
                task_id = row[0]
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
        """找新的 ready 任务（无依赖 or 依赖全 done），只返回已分配 agent 的任务"""
        try:
            with self.db.engine.connect() as conn:
                query = text(
                    "SELECT t.*, a.name as agent_name FROM tasks t "
                    "LEFT JOIN agents a ON t.assigned_agent = a.id "
                    "WHERE t.project_id = :project_id AND t.status = 'todo' "
                    "AND t.assigned_agent IS NOT NULL "
                    "AND NOT EXISTS ("
                    "  SELECT 1 FROM task_dependencies td "
                    "  JOIN tasks dep ON td.dependency_id = dep.id "
                    "  WHERE td.task_id = t.id AND dep.status != 'done'"
                    ") ORDER BY t.created_at ASC"
                )
                tasks = conn.execute(query, {"project_id": self.project_id}).fetchall()

                result = []
                for row in tasks:
                    agent_name = getattr(row, "agent_name", None) or "main"
                    result.append({
                        "id": row.id,
                        "title": row.title,
                        "description": row.description,
                        "project_id": row.project_id,
                        "assigned_agent": row.assigned_agent,
                        "agent_name": agent_name,
                        "status": row.status,
                        "acceptance_criteria": row.acceptance_criteria,
                        "verifier_agent_id": row.verifier_agent_id,
                        "created_at": row.created_at,
                    })

                # 注入当前轮次约束
                constraint_text = _get_constraint_text(conn, self.project_id)
                if constraint_text:
                    for task in result:
                        desc = task.get("description") or ""
                        task["description"] = f"{desc}\n\n⚙️ 当前约束：{constraint_text}"
                    logger.info(f"[ProjectExecutor] Injected constraints: {constraint_text}", flush=True)

                logger.info(f"[ProjectExecutor] Found {len(result)} ready tasks for project {self.project_id}", flush=True)
                return result
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


def _get_constraint_text(conn, project_id: str) -> str:
    """获取当前轮次约束文本，注入到任务描述中"""
    try:
        proj_row = conn.execute(
            text("SELECT goal_id FROM projects WHERE id = :pid"),
            {"pid": project_id},
        ).fetchone()
        if not proj_row:
            return ""
        goal_id = proj_row[0]

        cons_row = conn.execute(
            text(
                "SELECT constraints FROM iteration_constraints "
                "WHERE goal_id = :gid ORDER BY round DESC LIMIT 1"
            ),
            {"gid": goal_id},
        ).fetchone()
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
