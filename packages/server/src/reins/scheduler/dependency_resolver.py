"""
依赖解析器

职责：
1. 当任务完成时，检查是否有依赖它的任务
2. 如果依赖全部满足 → 解锁后续任务
3. 如果依赖未满足 → 保持 blocked/todo
"""

from loguru import logger
from datetime import datetime
from typing import List
from sqlalchemy import text

from reins.common.database import get_db_manager

class DependencyResolver:
    """依赖解析器"""

    def __init__(self, db_manager=None):
        self.db = db_manager or get_db_manager()

    def unlock_on_completion(self, completed_task_id: str) -> List[str]:
        """
        当任务完成时调用

        逻辑：
        1. 查询 task_dependencies 中 dependency_id = completed_task_id 的记录
        2. 对每个依赖该任务的 task：
           a. 检查该 task 的所有依赖是否都已完成
           b. 如果全部完成 → 更新 status = todo（从 blocked 恢复）
           c. 记录解锁日志

        返回：被解锁的任务 ID 列表
        """
        unlocked = []
        try:
            with self.db.engine.connect() as conn:
                # 找到依赖此任务的所有任务
                dependents = conn.execute(text("""
                    SELECT task_id FROM task_dependencies
                    WHERE dependency_id = :task_id
                """), {"task_id": completed_task_id}).fetchall()

                for (dependent_id,) in dependents:
                    # 检查该任务的所有依赖是否都已完成
                    all_deps_done = conn.execute(text("""
                        SELECT COUNT(*) FROM task_dependencies td
                        JOIN tasks t ON td.dependency_id = t.id
                        WHERE td.task_id = :task_id
                          AND t.status != 'done'
                    """), {"task_id": dependent_id}).fetchone()

                    if all_deps_done and all_deps_done[0] == 0:
                        # 所有依赖都已完成，解锁
                        conn.execute(text("""
                            UPDATE tasks
                            SET status = 'todo',
                                updated_at = :now
                            WHERE id = :task_id
                              AND status = 'blocked'
                        """), {"task_id": dependent_id, "now": datetime.now()})

                        unlocked.append(dependent_id)
                        logger.info(f"[DependencyResolver] Unlocked task {dependent_id}")

                conn.commit()

        except Exception as e:
            logger.error(f"[DependencyResolver] unlock_on_completion error: {e}")

        return unlocked

    def block_if_deps_not_met(self, task_id: str) -> bool:
        """
        当任务开始时检查依赖是否满足
        如果有未完成的依赖 → 标记为 blocked

        返回：是否被阻塞
        """
        try:
            with self.db.engine.connect() as conn:
                unfinished = conn.execute(text("""
                    SELECT COUNT(*) FROM task_dependencies td
                    JOIN tasks t ON td.dependency_id = t.id
                    WHERE td.task_id = :task_id
                      AND t.status NOT IN ('done', 'failed', 'timeout')
                """), {"task_id": task_id}).fetchone()

                if unfinished and unfinished[0] > 0:
                    conn.execute(text("""
                        UPDATE tasks
                        SET status = 'blocked',
                            blocked_reason = '依赖的任务尚未完成',
                            updated_at = :now
                        WHERE id = :task_id
                    """), {"task_id": task_id, "now": datetime.now()})
                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"[DependencyResolver] block_if_deps_not_met error: {e}")

        return False

    def scan_blocked(self) -> List[str]:
        """
        扫描所有 blocked 任务，检查是否可以解锁

        返回：可解锁的任务 ID 列表
        """
        unlockable = []
        try:
            with self.db.engine.connect() as conn:
                blocked = conn.execute(text("""
                    SELECT id FROM tasks WHERE status = 'blocked'
                """)).fetchall()

                for (task_id,) in blocked:
                    all_deps_done = conn.execute(text("""
                        SELECT COUNT(*) FROM task_dependencies td
                        JOIN tasks t ON td.dependency_id = t.id
                        WHERE td.task_id = :task_id
                          AND t.status != 'done'
                    """), {"task_id": task_id}).fetchone()

                    if all_deps_done and all_deps_done[0] == 0:
                        unlockable.append(task_id)

        except Exception as e:
            logger.error(f"[DependencyResolver] scan_blocked error: {e}")

        return unlockable

    def unlock_on_human_input(self, input_id: str) -> List[str]:
        """
        当人类输入被提交时调用

        逻辑：
        1. 根据 input_id 查找关联的 task_id
        2. 查询 task_dependencies 中依赖此 task_id 的任务
        3. 检查所有依赖是否都已完成 (done)
        4. 如果全部完成 → 解锁 (blocked -> todo)

        返回：被解锁的任务 ID 列表
        """
        unlocked = []
        try:
            with self.db.engine.connect() as conn:
                # a. 根据 input_id 查找关联的 task_id
                result = conn.execute(text("""
                    SELECT task_id FROM human_input_requests
                    WHERE id = :input_id
                """), {"input_id": input_id}).fetchone()

                if not result:
                    logger.warning(f"[DependencyResolver] unlock_on_human_input: input_id {input_id} not found")
                    return unlocked

                task_id = result[0]

                # b. 查询 task_dependencies 中依赖此任务的任务
                dependents = conn.execute(text("""
                    SELECT task_id FROM task_dependencies
                    WHERE dependency_id = :task_id
                """), {"task_id": task_id}).fetchall()

                for (dependent_id,) in dependents:
                    # c. 检查该任务的所有依赖是否都已完成
                    all_deps_done = conn.execute(text("""
                        SELECT COUNT(*) FROM task_dependencies td
                        JOIN tasks t ON td.dependency_id = t.id
                        WHERE td.task_id = :task_id
                          AND t.status != 'done'
                    """), {"task_id": dependent_id}).fetchone()

                    if all_deps_done and all_deps_done[0] == 0:
                        # d. 所有依赖都已完成，解锁
                        conn.execute(text("""
                            UPDATE tasks
                            SET status = 'todo',
                                updated_at = :now
                            WHERE id = :task_id
                              AND status = 'blocked'
                        """), {"task_id": dependent_id, "now": datetime.now()})

                        unlocked.append(dependent_id)
                        logger.info(f"[DependencyResolver] unlock_on_human_input: Unlocked task {dependent_id}")

                conn.commit()

        except Exception as e:
            logger.error(f"[DependencyResolver] unlock_on_human_input error: {e}")

        return unlocked
