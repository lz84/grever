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
from sqlalchemy import text

from api.app_state import get_db_manager

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

GENE_COLUMNS = [
    "id", "schema_version", "category", "signals_match", "preconditions",
    "strategy", "constraints", "validation", "epigenetic_marks",
    "asset_id", "created_at", "updated_at",
]


def _row_to_dict(row) -> dict:
    """将 SQLAlchemy Row 转为 dict，自动解析 JSON 列和 DateTime"""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    for json_col in ("signals_match", "preconditions", "strategy",
                     "constraints", "validation", "epigenetic_marks"):
        val = d.get(json_col)
        if isinstance(val, str):
            try:
                d[json_col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                d[json_col] = None
        elif val is None:
            d[json_col] = None
    for dt_col in ("created_at", "updated_at"):
        val = d.get(dt_col)
        if val is not None and not isinstance(val, str):
            d[dt_col] = str(val)
    return d


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

    where_clauses = []
    params: dict = {}

    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    if asset_id:
        where_clauses.append("asset_id = :asset_id")
        params["asset_id"] = asset_id

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    cols = ", ".join(GENE_COLUMNS)
    db = get_db_manager()

    # 总数查询
    count_sql = f"SELECT COUNT(*) FROM genes {where_sql}"
    with db.engine.connect() as conn:
        total = total = conn.execute(text(count_sql), params).scalar()

    # 分页查询
    offset = (page - 1) * page_size
    data_sql = (
        f"SELECT {cols} FROM genes {where_sql} "
        "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = page_size
    params["offset"] = offset

    with db.engine.connect() as conn:
        rows = rows = conn.execute(text(data_sql), params).fetchall()
    items = [_row_to_dict(r) for r in rows]

    return GeneListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ===========================================================================
# GET /api/v1/evo/genes/{gene_id} — 查询单个 Gene 详情
# ===========================================================================

@router.get("/{gene_id}")
def get_gene(gene_id: str):
    """查询单个 Gene 详情，不存在则返回 404"""
    cols = ", ".join(GENE_COLUMNS)
    db = get_db_manager()

    with db.engine.connect() as conn:
        row = row = conn.execute(
        text(f"SELECT {cols} FROM genes WHERE id = :id"),
        {"id": gene_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Gene not found: {gene_id}")

    return _row_to_dict(row)


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
    now = datetime.now().isoformat()

    db = get_db_manager()
    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO genes (
        id, schema_version, category, signals_match, preconditions,
        strategy, constraints, validation, epigenetic_marks,
        asset_id, created_at, updated_at
        ) VALUES (
        :id, :schema_version, :category, :signals_match, :preconditions,
        :strategy, :constraints, :validation, :epigenetic_marks,
        :asset_id, :created_at, :updated_at
        )
        """),
        {
        "id": gene_id,
        "schema_version": req.schema_version or "1.0",
        "category": req.category,
        "signals_match": json.dumps(req.signals_match, ensure_ascii=False) if req.signals_match else None,
        "preconditions": json.dumps(req.preconditions, ensure_ascii=False) if req.preconditions else None,
        "strategy": json.dumps(req.strategy, ensure_ascii=False) if req.strategy else None,
        "constraints": json.dumps(req.constraints, ensure_ascii=False) if req.constraints else None,
        "validation": json.dumps(req.validation, ensure_ascii=False) if req.validation else None,
        "epigenetic_marks": json.dumps(req.epigenetic_marks, ensure_ascii=False) if req.epigenetic_marks else None,
        "asset_id": req.asset_id,
        "created_at": now,
        "updated_at": now,
        },
        )
        conn.commit()

    logger.info("Gene %s created (category=%s)", gene_id, req.category)

    # 返回创建后的 Gene
    cols = ", ".join(GENE_COLUMNS)
    with db.engine.connect() as conn:
        created = created = conn.execute(
        text(f"SELECT {cols} FROM genes WHERE id = :id"),
        {"id": gene_id},
        ).fetchone()

    return _row_to_dict(created)


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
    db = get_db_manager()
    task_ids = req.task_ids

    if task_ids:
        placeholders = ", ".join(f":tid{i}" for i in range(len(task_ids)))
        task_params = {f"tid{i}": tid for i, tid in enumerate(task_ids)}
        with db.engine.connect() as conn:
            rows = rows = conn.execute(
            text(f"""
            SELECT id, title, category as task_category, assigned_agent,
            status, result, created_at, completed_at
            FROM tasks WHERE id IN ({placeholders})
            """),
            task_params,
            ).fetchall()
    else:
        # 提取最近的成功/失败任务
        with db.engine.connect() as conn:
            rows = rows = conn.execute(
            text("""
            SELECT id, title, category as task_category, assigned_agent,
            status, result, created_at, completed_at
            FROM tasks
            WHERE status IN ('completed', 'failed', 'timeout')
            ORDER BY created_at DESC
            LIMIT 100
            """),
            ).fetchall()

    # 转换为 distiller 所需的格式
    task_records = []
    for r in rows:
        record = {
            "task_id": r.id,
            "task_type": r.title or "unknown",
            "task_category": r.task_category,
            "assigned_agent": r.assigned_agent,
            "status": r.status or "unknown",
            "result": r.result,
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
        now = datetime.now().isoformat()

        with db.engine.connect() as conn:
            conn.execute(
            text("""
            INSERT OR REPLACE INTO genes (
            id, schema_version, category, signals_match, preconditions,
            strategy, constraints, validation, epigenetic_marks,
            asset_id, created_at, updated_at
            ) VALUES (
            :id, :schema_version, :category, :signals_match, :preconditions,
            :strategy, :constraints, :validation, :epigenetic_marks,
            :asset_id, :created_at, :updated_at
            )
            """),
            {
            "id": gene_id,
            "schema_version": gene.schema_version,
            "category": gene.category,
            "signals_match": json.dumps(gene.signals_match, ensure_ascii=False),
            "preconditions": json.dumps(gene.preconditions, ensure_ascii=False),
            "strategy": json.dumps(gene.strategy, ensure_ascii=False),
            "constraints": json.dumps(gene.constraints, ensure_ascii=False),
            "validation": json.dumps(gene.validation, ensure_ascii=False),
            "epigenetic_marks": json.dumps(
            [m.to_dict() for m in gene.epigenetic_marks],
            ensure_ascii=False,
            ),
            "asset_id": gene.asset_id,
            "created_at": now,
            "updated_at": now,
            },
            )
            conn.commit()
        persisted.append(gene_id)

    logger.info("Extracted and persisted %d genes", len(persisted))

    return {
        "genes_extracted": len(persisted),
        "gene_ids": persisted,
        "source_tasks": len(task_records),
    }
