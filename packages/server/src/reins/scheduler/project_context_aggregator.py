"""
Project context 自动汇总器 — Sprint 86d-3

职责：
1. 当 Project 下所有任务都完成时，自动汇总子任务的 context_md 到 project.context_md
2. 按任务顺序组织上下文，便于验证者和后续任务参考
"""

from loguru import logger
from typing import Optional
from sqlalchemy import text

def aggregate_project_context(project_id: str, db_manager) -> Optional[str]:
    """
    汇总 Project 下所有任务的 context_md 到 project.context_md。
    
    返回：汇总后的 context_md 字符串（如果所有任务都已完成）
    """
    conn = db_manager.engine.connect()
    try:
        # 1. 检查项目是否所有任务都已完成
        task_count = conn.execute(text("""
            SELECT COUNT(*) FROM tasks WHERE project_id = :pid
        """), {"pid": project_id}).fetchone()[0]
        
        if task_count == 0:
            logger.debug(f"[ProjectContextAggregator] No tasks in project {project_id}")
            return None
        
        done_count = conn.execute(text("""
            SELECT COUNT(*) FROM tasks 
            WHERE project_id = :pid AND status = 'done'
        """), {"pid": project_id}).fetchone()[0]
        
        if done_count < task_count:
            logger.debug(
                f"[ProjectContextAggregator] Project {project_id}: "
                f"{done_count}/{task_count} done, skipping aggregation"
            )
            return None
        
        # 2. 所有任务都已完成，汇总 context_md
        tasks = conn.execute(text("""
            SELECT id, title, context_md 
            FROM tasks 
            WHERE project_id = :pid 
            ORDER BY created_at ASC
        """), {"pid": project_id}).fetchall()
        
        if not tasks:
            return None
        
        parts = []
        parts.append(f"# 📁 工程上下文汇总（Project {project_id}）")
        parts.append("")
        parts.append(f"共 {len(tasks)} 个任务，全部完成。")
        parts.append("")
        
        for t in tasks:
            ctx_md = t.context_md or ""
            if ctx_md.strip():
                parts.append(f"## 📋 {t.title} (`{t.id}`)")
                parts.append(ctx_md)
                parts.append("")
        
        aggregated = "\n".join(parts)
        
        # 3. 写入 project.context_md
        conn.execute(text("""
            UPDATE projects 
            SET context_md = :ctx, updated_at = CURRENT_TIMESTAMP
            WHERE id = :pid
        """), {"ctx": aggregated, "pid": project_id})
        conn.commit()
        
        logger.info(
            f"[ProjectContextAggregator] Aggregated {len(tasks)} task contexts "
            f"for project {project_id} ({len(aggregated)} chars)"
        )
        
        return aggregated
        
    except Exception as e:
        logger.error(f"[ProjectContextAggregator] Failed to aggregate for project {project_id}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()
