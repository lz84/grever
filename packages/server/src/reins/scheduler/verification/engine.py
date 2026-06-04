"""
验证引擎 — ResultVerifier 主类

职责：
1. 验证器 tick 循环
2. trigger_verification 主流程
3. 主观检查派发
"""

from datetime import datetime
from typing import Dict, List

from loguru import logger
from sqlalchemy import text

from reins.common.config import MAX_VERIFICATION_CYCLES
from reins.scheduler.dependency_resolver import DependencyResolver
from reins.scheduler.verification.dispatcher import VerificationDispatcher
from reins.common.database import get_db_manager, get_db_session

from .rules import classify_criteria, run_objective_checks
from .arbitration import (
    handle_verification_passed,
    handle_review_needed,
    handle_disputed,
    handle_no_criteria,
)


class ResultVerifier:
    """结果验证器 — 薄分发层：客观检查直接执行，主观检查推给 Worker"""

    DEFAULT_VERIFIER = "3745f1f0-b67d-4287-a10b-e71b3ff17e97"
    MAX_VERIFICATION_CYCLES = MAX_VERIFICATION_CYCLES

    def __init__(self, db_manager=None):
        self.db = db_manager or get_db_manager()
        self.dependency_resolver = DependencyResolver(self.db)

    # ===== 公共方法 =====

    def resolve_effective_verifier(self, task_id: str) -> str:
        """解析任务的最终检查 Agent（三级继承链）"""
        with self.db.engine.connect() as conn:
            task = conn.execute(
                text("SELECT id, verifier_agent_id, project_id, goal_id FROM tasks WHERE id = :id"),
                {"id": task_id},
            ).fetchone()
            if not task:
                return self.DEFAULT_VERIFIER
            if task.verifier_agent_id:
                return task.verifier_agent_id
            if task.project_id:
                project = conn.execute(
                    text("SELECT verifier_agent_id FROM projects WHERE id = :id"),
                    {"id": task.project_id},
                ).fetchone()
                if project and project.verifier_agent_id:
                    return project.verifier_agent_id
            if task.goal_id:
                goal = conn.execute(
                    text("SELECT verifier_agent_id FROM goals WHERE id = :id"),
                    {"id": task.goal_id},
                ).fetchone()
                if goal and goal.verifier_agent_id:
                    return goal.verifier_agent_id
        return self.DEFAULT_VERIFIER

    def tick(self) -> Dict:
        """
        验证器 tick — 独立扫描 review_needed 任务并验证。
        被 Scheduler tick 循环调用（Step 7）。
        """
        with self.db.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, result_summary, status, context_md FROM tasks "
                    "WHERE status = 'review_needed' ORDER BY updated_at ASC LIMIT 50"
                )
            ).fetchall()

            if not rows:
                return {"processed_count": 0, "passed": 0, "failed": 0}

            processed = passed = failed = 0
            for row in rows:
                task_id = row.id
                result_text = row.result_summary or ""
                context = row.context_md or None
                try:
                    verify_result = self.trigger_verification(
                        task_id, result_text, True, context_md=context
                    )
                    processed += 1
                    if verify_result.get("passed"):
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"[ResultVerifier] tick failed for {task_id}: {e}")
                    failed += 1

            return {"processed_count": processed, "passed": passed, "failed": failed}

    def trigger_verification(
        self, task_id: str, result: str, success: bool, context_md: str = None
    ) -> Dict:
        """
        薄分发层：按 acceptance_criteria 类型分类
        1. 解析 acceptance_criteria
        2. 客观检查直接执行
        3. 主观检查推给 Worker Agent
        4. 汇总结果写 comment
        5. 全部通过→done，不通过→review_needed
        """
        effective_verifier = self.resolve_effective_verifier(task_id)

        with self.db.engine.connect() as conn:
            row = conn.execute(
                text("SELECT verification_cycle, context_md FROM tasks WHERE id = :id"),
                {"id": task_id},
            ).fetchone()
            current_cycle = (row.verification_cycle or 0) if row else 0

        if context_md is None:
            with self.db.engine.connect() as conn:
                row = conn.execute(
                    text("SELECT context_md FROM tasks WHERE id = :id"),
                    {"id": task_id},
                ).fetchone()
                context_md = row.context_md if row else None

        # 分类验收标准
        objective_criteria, subjective_criteria = classify_criteria(self.db, task_id)

        cycle = current_cycle + 1

        # 无验收标准 → review_needed
        if not objective_criteria and not subjective_criteria:
            return handle_no_criteria(self.db, task_id, effective_verifier, cycle, self.MAX_VERIFICATION_CYCLES)

        # 执行客观检查
        objective_results = run_objective_checks(self.db, objective_criteria, task_id, context_md)
        logger.info(f"[ResultVerifier] Objective checks: {len(objective_results)} executed")

        # 主观检查推给 Worker
        subjective_results = self._dispatch_to_worker(task_id, subjective_criteria, result)
        logger.info(f"[ResultVerifier] Subjective checks: {len(subjective_results)} dispatched")

        # 汇总结果
        all_results = objective_results + subjective_results
        all_passed = all(r.get("passed", False) for r in all_results)
        failed_results = [r for r in all_results if not r.get("passed", False)]

        if all_passed:
            message = f"All {len(all_results)} checks passed"
            if objective_results:
                message += f" ({len(objective_results)} objective"
                if subjective_results:
                    message += f", {len(subjective_results)} subjective"
                message += ")"
        else:
            details = "; ".join(f"{r['name']}: {r['detail']}" for r in failed_results)
            message = f"{len(failed_results)}/{len(all_results)} checks failed: {details}"

        # 获取任务信息用于后续处理
        with self.db.engine.connect() as conn:
            t = conn.execute(
                text("SELECT assigned_agent, goal_id, project_id FROM tasks WHERE id = :id"),
                {"id": task_id},
            ).fetchone()
            assigned_agent = t.assigned_agent if t else None
            goal_id = t.goal_id if t else None
            project_id = t.project_id if t else None

        checks = all_results

        if all_passed:
            return handle_verification_passed(
                self.db, task_id, effective_verifier, cycle, message, checks,
                self.MAX_VERIFICATION_CYCLES,
                assigned_agent=assigned_agent, goal_id=goal_id, project_id=project_id,
            )
        else:
            if cycle >= self.MAX_VERIFICATION_CYCLES:
                return handle_disputed(
                    self.db, task_id, effective_verifier, cycle, message, checks,
                    self.MAX_VERIFICATION_CYCLES,
                    goal_id=goal_id, assigned_agent=assigned_agent,
                )
            else:
                return handle_review_needed(
                    self.db, task_id, effective_verifier, cycle, message, checks,
                    self.MAX_VERIFICATION_CYCLES,
                    assigned_agent=assigned_agent, goal_id=goal_id,
                )

    def verify(self, task_id: str, result: str, success: bool = True) -> Dict:
        """验证任务结果 — 统一走 trigger_verification 流程"""
        return self.trigger_verification(task_id, result, success)

    # ===== 主观检查派发 =====

    def _dispatch_to_worker(self, task_id: str, subjective_checks: List[Dict], result: str) -> List[Dict]:
        """
        主观检查通过 VerificationDispatcher 派发给验证智能体。
        """
        if not subjective_checks:
            return []

        dispatcher = VerificationDispatcher(get_db_session)
        checks_results: List[Dict] = []

        for check in subjective_checks:
            name = check.get("name", check.get("type", "unknown"))
            check_type = check.get("type", "subjective")
            desc = check.get("desc", "")

            acceptance_criteria = __import__("json").dumps({
                "name": name,
                "type": check_type,
                "description": desc,
            }, ensure_ascii=False)

            artifacts = {
                "result_summary": result[:3000] if result else "",
                "task_id": task_id,
                "check_name": name,
            }

            try:
                vr = dispatcher.dispatch(
                    task_id=task_id,
                    result_summary=result[:3000] if result else "",
                    acceptance_criteria=acceptance_criteria,
                    artifacts=artifacts,
                    verifier_type=check_type,
                )

                if vr.agent_id is None:
                    checks_results.append({
                        "name": name, "type": "subjective", "passed": False,
                        "detail": "无验证智能体，需人工审核", "evidence": vr.evidence,
                    })
                else:
                    checks_results.append({
                        "name": name, "type": "subjective",
                        "passed": vr.passed, "detail": vr.message, "evidence": vr.evidence,
                    })
            except Exception as e:
                logger.error(
                    f"[ResultVerifier] Verification dispatch error for check '{name}', task={task_id}: {e}",
                    exc_info=True,
                )
                checks_results.append({
                    "name": name, "type": "subjective", "passed": False,
                    "detail": f"验证超时: {str(e)}", "evidence": {"error": str(e)},
                })

        return checks_results
