"""
Evo 蒸馏触发器

从 DB 读取已完成的任务记录，运行蒸馏，固化模式，更新匹配权重。

用法:
    cd packages/server/src
    python -m evo.trigger_distill [--lookback DAYS]
"""

import json
import logging
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

# 确保能导入 evo 模块
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

DB_PATH = str(Path(__file__).resolve().parents[4] / "data" / "reins.db")

logger = logging.getLogger("evo.trigger")


def gather_task_records(db_path: str, lookback_days: int = 90) -> list[dict]:
    """
    从 DB 收集任务执行记录，用于蒸馏。
    """
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    cutoff = int((datetime.now() - timedelta(days=lookback_days)).timestamp())

    rows = c.execute("""
        SELECT 
            t.id, t.title, t.status, t.assigned_agent,
            t.project_id, t.capability_tags,
            t.created_at, t.completed_at, t.error_type, t.error_message,
            a.name as agent_name, a.capability_tags as agent_caps,
            t.result_summary
        FROM tasks t
        LEFT JOIN agents a ON t.assigned_agent = a.id
        WHERE t.status IN ('done', 'failed', 'error', 'timeout')
          AND t.assigned_agent IS NOT NULL
          AND t.assigned_agent != ''
          AND (
              t.completed_at >= ?
              OR (typeof(t.completed_at) = 'text' AND t.completed_at >= ?)
          )
        ORDER BY t.completed_at ASC
    """, (cutoff, cutoff)).fetchall()

    records = []
    for row in rows:
        agent_caps = {}
        if row["agent_caps"]:
            try:
                agent_caps = json.loads(row["agent_caps"]) if isinstance(row["agent_caps"], str) else row["agent_caps"]
            except Exception:
                agent_caps = {}

        agent_cap_list = []
        if isinstance(agent_caps, dict):
            for dim, vals in agent_caps.items():
                if isinstance(vals, list):
                    agent_cap_list.extend(vals)

        # 计算执行时长（completed_at 和 created_at 可能是整数时间戳或 ISO 字符串）
        duration_ms = None
        ca = row["completed_at"]
        ta = row["created_at"]
        if ca is not None and ta is not None:
            try:
                if isinstance(ca, (int, float)) and isinstance(ta, (int, float)):
                    duration_ms = int((ca - ta) * 1000)
                else:
                    t1 = datetime.fromisoformat(str(ta))
                    t2 = datetime.fromisoformat(str(ca))
                    duration_ms = int((t2 - t1).total_seconds() * 1000)
            except Exception:
                pass

        records.append({
            "task_id": row["id"],
            "task_title": row["title"],
            "task_type": _guess_task_type(row["title"]),
            "task_category": "general",
            "required_capabilities": [],
            "assigned_agent": row["assigned_agent"],
            "agent_capabilities": agent_caps,
            "agent_cap_list": agent_cap_list,
            "status": _map_status(row["status"]),
            "quality_score": 0.8 if row["status"] == "done" else 0.2,
            "duration_ms": duration_ms,
            "error_type": row["error_type"] or "",
            "error_message": row["error_message"] or "",
            "project_id": row["project_id"],
            "result_summary": row["result_summary"] or "",
            "completed_at": str(row["completed_at"]) if row["completed_at"] else None,
        })

    db.close()
    logger.info(f"Collected {len(records)} task records for distillation")
    return records


def _guess_task_type(title: str) -> str:
    if not title:
        return "unknown"
    title_lower = title.lower()
    if any(k in title_lower for k in ["coding", "开发", "代码", "fix", "bug"]):
        return "coding"
    if any(k in title_lower for k in ["design", "设计", "ui", "frontend", "前端"]):
        return "design"
    if any(k in title_lower for k in ["test", "测试", "e2e"]):
        return "testing"
    if any(k in title_lower for k in ["research", "调研", "分析"]):
        return "research"
    if any(k in title_lower for k in ["doc", "文档", "write"]):
        return "documentation"
    if any(k in title_lower for k in ["deploy", "部署", "infra", "ops"]):
        return "devops"
    if any(k in title_lower for k in ["migrate", "迁移", "refactor", "重构", "clean"]):
        return "refactoring"
    return "general"


def _map_status(status: str) -> str:
    if status == "done":
        return "success"
    if status in ("failed", "error", "timeout"):
        return status
    return "unknown"


def run_distillation(db_path: str = DB_PATH, lookback_days: int = 90):
    """运行完整的蒸馏流程"""
    from evo.distillation.distiller import RuleDistiller
    from evo.distillation.solidify import Solidifier, PatternStatus
    from evo.weight.weight_updater import WeightUpdater

    logger.info(f"=== Evo 蒸馏开始 (lookback={lookback_days} days) ===")

    # 1. 收集任务记录
    records = gather_task_records(db_path, lookback_days)
    if not records:
        logger.info("No task records found, skipping distillation")
        return

    success_count = sum(1 for r in records if r["status"] == "success")
    fail_count = len(records) - success_count
    logger.info(f"  总计: {len(records)} 条, 成功: {success_count}, 失败: {fail_count}")

    # 2. 提取 Gene
    distiller = RuleDistiller(min_support=2, min_confidence=0.3)
    genes = distiller.distill(records)
    logger.info(f"  提取了 {len(genes)} 个 Gene")

    for g in genes:
        logger.info(f"    Gene {g.id}: category={g.category}, confidence={g.confidence:.2f}, support={g.support_count}")

    # 3. 固化为 Capsule
    solidifier = Solidifier()
    capsules = solidifier.solidify(genes)
    logger.info(f"  固化了 {len(capsules)} 个 Capsule")

    for c in capsules:
        logger.info(f"    Capsule {c.id}: gene_id={c.gene_id}, confidence={c.confidence:.2f}, status={c.status}")

    # 4. 初始化权重更新器，设置当前 Agent 权重快照
    updater = WeightUpdater()

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    agents = db.execute("SELECT id, capability_tags FROM agents").fetchall()
    for agent in agents:
        caps = {}
        if agent["capability_tags"]:
            try:
                caps = json.loads(agent["capability_tags"]) if isinstance(agent["capability_tags"], str) else agent["capability_tags"]
            except Exception:
                pass
        all_caps = []
        if isinstance(caps, dict):
            for dim, vals in caps.items():
                if isinstance(vals, list):
                    all_caps.extend(vals)
        weights = {cap: 1.0 for cap in all_caps}
        updater.set_agent_weights(agent["id"], weights)

    # 5. 应用模式权重
    weight_events = updater.apply_patterns(capsules)
    logger.info(f"  应用了 {len(weight_events)} 个权重更新")

    for ev in weight_events[:10]:
        logger.info(f"    {ev.id}: {ev.target_id}.{ev.field_name} {ev.old_value} → {ev.new_value}")

    # 6. 写入 DB
    conn = db
    # 写入 Genes
    for gene in genes:
        conn.execute("""
            INSERT OR REPLACE INTO genes 
            (id, schema_version, category, signals_match, preconditions, strategy, 
             constraints, validation, epigenetic_marks, asset_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            gene.id, gene.schema_version, gene.category,
            json.dumps(gene.signals_match, ensure_ascii=False),
            json.dumps(gene.preconditions, ensure_ascii=False),
            json.dumps(gene.strategy, ensure_ascii=False),
            json.dumps(gene.constraints, ensure_ascii=False),
            json.dumps(gene.validation, ensure_ascii=False),
            json.dumps([m.to_dict() for m in gene.epigenetic_marks], ensure_ascii=False),
            gene.asset_id or None,
        ))

    # 写入 Capsules
    for capsule in capsules:
        conn.execute("""
            INSERT OR REPLACE INTO capsules
            (id, schema_version, trigger, gene_id, summary, confidence,
             blast_radius, outcome, success_streak, content, diff, strategy, a2a)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            capsule.id, capsule.schema_version,
            json.dumps(capsule.trigger, ensure_ascii=False),
            capsule.gene_id,
            capsule.summary,
            capsule.confidence,
            json.dumps(capsule.blast_radius, ensure_ascii=False),
            json.dumps(capsule.outcome, ensure_ascii=False),
            capsule.success_streak,
            capsule.content or "",
            capsule.diff or "",
            json.dumps(capsule.strategy, ensure_ascii=False),
            json.dumps(capsule.a2a, ensure_ascii=False),
        ))

    # 写入 EvolutionEvents
    for ev in weight_events:
        conn.execute("""
            INSERT OR REPLACE INTO evolution_events
            (id, schema_version, parent_id, intent, signals, genes_used,
             mutation_id, blast_radius, outcome, capsule_id, env_fingerprint, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ev.id, ev.schema_version, ev.parent_id,
            ev.intent,
            json.dumps(ev.signals, ensure_ascii=False),
            json.dumps(ev.genes_used, ensure_ascii=False),
            ev.mutation_id,
            json.dumps(ev.blast_radius, ensure_ascii=False),
            json.dumps(ev.outcome, ensure_ascii=False),
            ev.capsule_id,
            json.dumps(ev.env_fingerprint, ensure_ascii=False),
            json.dumps(ev.meta, ensure_ascii=False),
        ))

    # 更新 agent_tag_weights
    for agent_id, weights in updater.get_current_all_weights().items():
        if agent_id == "_global":
            continue
        for tag, weight in weights.items():
            existing = conn.execute(
                "SELECT 1 FROM agent_tag_weights WHERE agent_id = ? AND tag = ?",
                (agent_id, tag),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE agent_tag_weights SET weight = ?, last_observed = CURRENT_TIMESTAMP "
                    "WHERE agent_id = ? AND tag = ?",
                    (weight, agent_id, tag))
            else:
                conn.execute(
                    "INSERT INTO agent_tag_weights (agent_id, tag, weight, last_observed) "
                    "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                    (agent_id, tag, weight))

    conn.commit()
    db.close()

    logger.info("=== Evo 蒸馏完成 ===")
    return {
        "records_count": len(records),
        "genes_count": len(genes),
        "capsules_count": len(capsules),
        "weight_updates_count": len(weight_events),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evo 蒸馏触发器")
    parser.add_argument("--lookback", type=int, default=90, help="回溯天数")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_distillation(lookback_days=args.lookback)
    print(json.dumps(result, indent=2, ensure_ascii=False))
