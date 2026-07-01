"""
Evo 进化域 - Distillation API

提供经验蒸馏、Capsule 固化、能力进化端点。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import Gene, Capsule, Task, Agent
from reins.common.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/evo", tags=["evo-distillation"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================


class DistillRequest(BaseModel):
    """经验蒸馏请求"""
    task_ids: Optional[list[str]] = None
    min_support: int = 2
    min_confidence: float = 0.5
    category: Optional[str] = None


class SolidifyRequest(BaseModel):
    """Capsule 固化请求"""
    gene_id: str
    summary: str
    content: Optional[str] = None
    diff: Optional[str] = None
    trigger: Optional[list[str]] = None
    strategy: Optional[list[dict]] = None
    confidence: Optional[float] = None
    blast_radius: Optional[dict] = None


class EvolveCapabilitiesRequest(BaseModel):
    """能力进化请求"""
    agent_id: Optional[str] = None
    gene_ids: Optional[list[str]] = None
    target_capabilities: Optional[list[str]] = None


class DistillResponse(BaseModel):
    genes_extracted: int
    gene_ids: list[str]
    source_tasks: int


class SolidifyResponse(BaseModel):
    capsule_id: str
    gene_id: str
    status: str


class EvolveResponse(BaseModel):
    evolved_count: int
    capabilities: list[dict]
    agent_id: Optional[str] = None


# ===========================================================================
# POST /api/v1/evo/distill — 经验蒸馏
# ===========================================================================

@router.post("/distill")
def distill_experience(req: DistillRequest):
    """
    从任务执行记录中蒸馏经验，提取 Gene。

    - 不指定 task_ids 时，自动提取最近的成功/失败任务
    - 返回提取的 Gene 列表
    """
    from evo.distillation.distiller import RuleDistiller

    db = get_db_session()
    try:
        # 获取任务记录
        if req.task_ids:
            rows = db.query(Task).with_entities(
                Task.id, Task.title, Task.assigned_agent,
                Task.status, Task.result, Task.created_at, Task.completed_at,
            ).filter(Task.id.in_(req.task_ids)).all()
        else:
            rows = db.query(Task).with_entities(
                Task.id, Task.title, Task.assigned_agent,
                Task.status, Task.result, Task.created_at, Task.completed_at,
            ).filter(
                Task.status.in_(['completed', 'failed', 'timeout'])
            ).order_by(
                Task.created_at.desc()
            ).limit(100).all()

        task_records = []
        for r in rows:
            task_records.append({
                "task_id": r[0],
                "task_type": r[1] or "unknown",
                "assigned_agent": r[2],
                "status": r[3] or "unknown",
                "result": r[4],
            })

        if not task_records:
            return {"genes_extracted": 0, "gene_ids": [], "source_tasks": 0,
                    "message": "No task records found for distillation"}

        # 执行蒸馏
        distiller = RuleDistiller(
            min_support=req.min_support,
            min_confidence=req.min_confidence,
        )
        genes = distiller.distill(task_records)

        # 按类别过滤
        if req.category:
            genes = [g for g in genes if g.category == req.category]

        # 持久化 Gene
        persisted_ids = []
        for gene in genes:
            gene_id = gene.id or str(uuid.uuid4())
            now = datetime.now()

            existing = db.query(Gene).filter(Gene.id == gene_id).first()
            if existing:
                existing.schema_version = gene.schema_version
                existing.category = gene.category
                existing.signals_match = json.dumps(gene.signals_match, ensure_ascii=False)
                existing.preconditions = json.dumps(gene.preconditions, ensure_ascii=False)
                existing.strategy = json.dumps(gene.strategy, ensure_ascii=False)
                existing.constraints = json.dumps(gene.constraints, ensure_ascii=False)
                existing.validation = json.dumps(gene.validation, ensure_ascii=False)
                existing.epigenetic_marks = json.dumps(
                    [m.to_dict() for m in gene.epigenetic_marks], ensure_ascii=False
                )
                existing.asset_id = gene.asset_id
                existing.updated_at = str(now)
            else:
                db.add(Gene(
                    id=gene_id,
                    schema_version=gene.schema_version,
                    category=gene.category,
                    signals_match=json.dumps(gene.signals_match, ensure_ascii=False),
                    preconditions=json.dumps(gene.preconditions, ensure_ascii=False),
                    strategy=json.dumps(gene.strategy, ensure_ascii=False),
                    constraints=json.dumps(gene.constraints, ensure_ascii=False),
                    validation=json.dumps(gene.validation, ensure_ascii=False),
                    epigenetic_marks=json.dumps(
                        [m.to_dict() for m in gene.epigenetic_marks], ensure_ascii=False
                    ),
                    asset_id=gene.asset_id,
                    created_at=str(now),
                    updated_at=str(now),
                ))
            persisted_ids.append(gene_id)

        db.commit()
        logger.info("Distilled %d genes from %d tasks", len(persisted_ids), len(task_records))

        return {
            "genes_extracted": len(persisted_ids),
            "gene_ids": persisted_ids,
            "source_tasks": len(task_records),
        }
    finally:
        db.close()


# ===========================================================================
# POST /api/v1/evo/solidify — Capsule 固化
# ===========================================================================

@router.post("/solidify")
def solidify_capsule(req: SolidifyRequest):
    """
    将 Gene 固化为 Capsule。

    Capsule 是可在实际执行中复用的记忆体。
    """
    db = get_db_session()
    try:
        # 验证 Gene 存在
        gene_row = db.query(Gene).with_entities(Gene.id, Gene.category).filter(
            Gene.id == req.gene_id
        ).first()

        if gene_row is None:
            raise HTTPException(status_code=404, detail=f"Gene not found: {req.gene_id}")

        capsule_id = f"cap-{uuid.uuid4().hex[:12]}"
        now = datetime.now()

        # 创建 Capsule
        db.add(Capsule(
            id=capsule_id,
            schema_version=1,
            trigger=json.dumps(req.trigger, ensure_ascii=False) if req.trigger else None,
            gene_id=req.gene_id,
            summary=req.summary,
            confidence=req.confidence if req.confidence is not None else 0.5,
            blast_radius=json.dumps(req.blast_radius, ensure_ascii=False) if req.blast_radius else None,
            outcome=json.dumps({"status": "draft"}, ensure_ascii=False),
            success_streak=0,
            content=req.content,
            diff=req.diff,
            strategy=json.dumps(req.strategy, ensure_ascii=False) if req.strategy else None,
            created_at=str(now),
        ))
        db.commit()

        logger.info("Capsule %s solidified from gene %s", capsule_id, req.gene_id)

        return {
            "capsule_id": capsule_id,
            "gene_id": req.gene_id,
            "status": "draft",
        }
    finally:
        db.close()


# ===========================================================================
# POST /api/v1/evo/evolve-capabilities — 能力进化
# ===========================================================================

@router.post("/evolve-capabilities")
def evolve_capabilities(req: EvolveCapabilitiesRequest):
    """
    基于 Gene 进化 Agent 能力。

    - 如果指定 agent_id，针对特定 Agent 进化
    - 如果指定 gene_ids，使用指定的 Gene 集合
    - 否则使用所有高置信度 Gene 进行全局进化
    """
    db = get_db_session()
    try:
        # 确定要使用的 Gene
        if req.gene_ids:
            gene_rows = db.query(Gene).with_entities(
                Gene.id, Gene.category, Gene.strategy, Gene.constraints,
            ).filter(Gene.id.in_(req.gene_ids)).all()
        elif req.agent_id:
            # 验证 Agent 存在
            agent_row = db.query(Agent).with_entities(Agent.id, Agent.capability_tags).filter(
                Agent.id == req.agent_id
            ).first()

            if agent_row is None:
                raise HTTPException(status_code=404, detail=f"Agent not found: {req.agent_id}")

            gene_rows = db.query(Gene).with_entities(
                Gene.id, Gene.category, Gene.strategy, Gene.constraints,
            ).filter(
                Gene.category.in_(['capability', 'pattern', 'optimize'])
            ).order_by(
                Gene.created_at.desc()
            ).limit(20).all()
        else:
            # 全局进化：使用所有高置信度 Gene
            gene_rows = db.query(Gene).with_entities(
                Gene.id, Gene.category, Gene.strategy, Gene.constraints,
            ).filter(
                Gene.category.in_(['capability', 'pattern', 'optimize'])
            ).order_by(
                Gene.created_at.desc()
            ).limit(50).all()

        # 构建进化后的能力
        evolved_capabilities = []
        for gr in gene_rows:
            strategy = gr[2]
            if isinstance(strategy, str):
                try:
                    strategy = json.loads(strategy)
                except (json.JSONDecodeError, TypeError):
                    strategy = []

            constraints = gr[3]
            if isinstance(constraints, str):
                try:
                    constraints = json.loads(constraints)
                except (json.JSONDecodeError, TypeError):
                    constraints = {}

            evolved_capabilities.append({
                "gene_id": gr[0],
                "category": gr[1],
                "strategy": strategy,
                "constraints": constraints,
            })

        # 如果指定了 Agent，更新其 capability_tags
        if req.agent_id and evolved_capabilities:
            capability_tags = {
                "evolved_at": datetime.now().isoformat(),
                "gene_count": len(evolved_capabilities),
                "tags": [ec["category"] for ec in evolved_capabilities],
            }
            db.query(Agent).filter(Agent.id == req.agent_id).update({
                "capability_tags": json.dumps(capability_tags, ensure_ascii=False),
            })
            db.commit()
            logger.info(
                "Evolved %d capabilities for agent %s",
                len(evolved_capabilities), req.agent_id,
            )

        return {
            "evolved_count": len(evolved_capabilities),
            "capabilities": evolved_capabilities,
            "agent_id": req.agent_id,
        }
    finally:
        db.close()
