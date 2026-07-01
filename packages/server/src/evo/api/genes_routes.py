"""
Evo 进化域 - Genes 管理 API

提供 Gene 的 CRUD 和特征提取端点。
直接操作 genes DB 表。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from models import Gene, Task
from reins.common.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/evo/genes", tags=["evo-genes"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================

VALID_CATEGORIES = {
    "capability", "pattern", "anti_pattern", "sequence",
    "condition", "constraint", "repair", "optimize", "innovation",
}


class GeneCreate(BaseModel):
    category: str
    signals_match: Optional[list[str]] = None
    preconditions: Optional[list[str]] = None
    strategy: Optional[list[dict]] = None
    constraints: Optional[dict] = None
    validation: Optional[list[str]] = None
    epigenetic_marks: Optional[list[dict]] = None
    asset_id: Optional[str] = None
    schema_version: Optional[str] = "1.0"


class GeneExtractRequest(BaseModel):
    """特征提取请求"""
    task_ids: Optional[list[str]] = None
    category: Optional[str] = None
    min_support: int = 2
    min_confidence: float = 0.5


class GeneListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


# ===========================================================================
# 辅助函数
# ===========================================================================


def _gene_to_dict(gene: Gene) -> dict:
    """将 Gene ORM 对象转为 dict，自动解析 JSON 列"""
    def _parse_json(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value

    return {
        "id": gene.id,
        "schema_version": gene.schema_version,
        "category": gene.category,
        "signals_match": _parse_json(gene.signals_match),
        "preconditions": _parse_json(gene.preconditions),
        "strategy": _parse_json(gene.strategy),
        "constraints": _parse_json(gene.constraints),
        "validation": _parse_json(gene.validation),
        "epigenetic_marks": _parse_json(gene.epigenetic_marks),
        "asset_id": gene.asset_id,
        "created_at": gene.created_at,
        "updated_at": gene.updated_at,
    }


# ===========================================================================
# GET /api/v1/evo/genes — 查询 Gene 列表
# ===========================================================================

@router.get("/")
def list_genes(
    category: Optional[str] = Query(None, description="按类别过滤"),
    asset_id: Optional[str] = Query(None, description="按资源 ID 过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """查询 Gene 列表，支持 category 和 asset_id 过滤，分页"""
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {category}. Must be one of {VALID_CATEGORIES}",
        )

    db = get_db_session()
    try:
        query = db.query(Gene)
        count_query = db.query(Gene)

        if category:
            query = query.filter(Gene.category == category)
            count_query = count_query.filter(Gene.category == category)

        if asset_id:
            query = query.filter(Gene.asset_id == asset_id)
            count_query = count_query.filter(Gene.asset_id == asset_id)

        total = count_query.count()

        offset = (page - 1) * page_size
        rows = query.order_by(Gene.created_at.desc()).offset(offset).limit(page_size).all()
        items = [_gene_to_dict(r) for r in rows]

        return GeneListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        db.close()


# ===========================================================================
# GET /api/v1/evo/genes/{gene_id} — 查询单个 Gene 详情
# ===========================================================================

@router.get("/{gene_id}")
def get_gene(gene_id: str):
    """查询单个 Gene 详情，不存在则返回 404"""
    db = get_db_session()
    try:
        row = db.query(Gene).filter(Gene.id == gene_id).first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Gene not found: {gene_id}")

        return _gene_to_dict(row)
    finally:
        db.close()


# ===========================================================================
# POST /api/v1/evo/genes — 创建 Gene
# ===========================================================================

@router.post("/")
def create_gene(req: GeneCreate):
    """
    创建新的 Gene。
    """
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {req.category}. Must be one of {VALID_CATEGORIES}",
        )

    gene_id = str(uuid.uuid4())
    now = str(datetime.now())

    db = get_db_session()
    try:
        new_gene = Gene(
            id=gene_id,
            schema_version=req.schema_version or "1.0",
            category=req.category,
            signals_match=json.dumps(req.signals_match, ensure_ascii=False) if req.signals_match else None,
            preconditions=json.dumps(req.preconditions, ensure_ascii=False) if req.preconditions else None,
            strategy=json.dumps(req.strategy, ensure_ascii=False) if req.strategy else None,
            constraints=json.dumps(req.constraints, ensure_ascii=False) if req.constraints else None,
            validation=json.dumps(req.validation, ensure_ascii=False) if req.validation else None,
            epigenetic_marks=json.dumps(req.epigenetic_marks, ensure_ascii=False) if req.epigenetic_marks else None,
            asset_id=req.asset_id,
            created_at=now,
            updated_at=now,
        )
        db.add(new_gene)
        db.commit()

        logger.info("Gene %s created (category=%s)", gene_id, req.category)

        # 返回创建后的 Gene
        created = db.query(Gene).filter(Gene.id == gene_id).first()
        return _gene_to_dict(created)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ===========================================================================
# POST /api/v1/evo/genes/extract — 特征提取
# ===========================================================================

@router.post("/extract")
def extract_genes(req: GeneExtractRequest):
    """
    从任务记录中提取 Gene 特征。
    调用 RuleDistiller 执行提取并将结果持久化。
    """
    from evo.distillation.distiller import RuleDistiller

    if req.category and req.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {req.category}",
        )

    # 获取任务记录
    db = get_db_session()
    try:
        task_ids = req.task_ids

        if task_ids:
            rows = db.query(Task).with_entities(
                Task.id, Task.title, Task.assigned_agent,
                Task.status, Task.result,
            ).filter(Task.id.in_(task_ids)).all()
        else:
            # 提取最近的成功/失败任务
            rows = db.query(Task).with_entities(
                Task.id, Task.title, Task.assigned_agent,
                Task.status, Task.result,
            ).filter(
                Task.status.in_(['completed', 'failed', 'timeout'])
            ).order_by(
                Task.created_at.desc()
            ).limit(100).all()

        # 转换为 distiller 所需的格式
        task_records = []
        for r in rows:
            record = {
                "task_id": r[0],
                "task_type": r[1] or "unknown",
                "assigned_agent": r[2],
                "status": r[3] or "unknown",
                "result": r[4],
            }
            task_records.append(record)

        if not task_records:
            return {"genes_extracted": 0, "message": "No task records found for extraction"}

        # 执行提取
        distiller = RuleDistiller(
            min_support=req.min_support,
            min_confidence=req.min_confidence,
        )
        genes = distiller.distill(task_records)

        # 过滤类别
        if req.category:
            genes = [g for g in genes if g.category == req.category]

        # 持久化提取的 Gene
        persisted = []
        for gene in genes:
            gene_id = gene.id or str(uuid.uuid4())
            now = str(datetime.now())

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
                existing.updated_at = now
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
                    created_at=now,
                    updated_at=now,
                ))
            persisted.append(gene_id)

        db.commit()
        logger.info("Extracted and persisted %d genes", len(persisted))

        return {
            "genes_extracted": len(persisted),
            "gene_ids": persisted,
            "source_tasks": len(task_records),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
