"""
注入管理 API 路由

MAK-190: 注入管理 API - 完整 CRUD + 状态端点
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from pydantic import BaseModel

from reins.common.database import get_db
from sqlalchemy import text

router = APIRouter(prefix="/api/v1/grasp/inject", tags=["grasp-inject"])

# ========== Pydantic 模型 ==========

class InjectRuleCreate(BaseModel):
    """创建注入规则请求"""
    name: str
    trigger_condition: str
    target_kb: str = "default"
    enabled: bool = True

class InjectRuleUpdate(BaseModel):
    """更新注入规则请求"""
    name: Optional[str] = None
    trigger_condition: Optional[str] = None
    target_kb: Optional[str] = None
    enabled: Optional[bool] = None

class InjectRuleResponse(BaseModel):
    """注入规则响应"""
    id: str
    name: str
    trigger_condition: str
    target_kb: str
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class InjectStatusResponse(BaseModel):
    """注入状态响应"""
    rules_enabled: int
    rules_disabled: int
    total_rules: int

# ========== 实际实现 ==========

@router.get("/rules", response_model=List[InjectRuleResponse])
def list_inject_rules(
    db: Session = Depends(get_db),
    enabled: Optional[int] = Query(None, description="筛选启用状态: 1=启用, 0=禁用")
):
    """获取注入规则列表，支持 enabled 筛选"""
    try:
        if enabled is not None:
            stmt = text("SELECT * FROM grasp_inject_rules WHERE enabled = :enabled ORDER BY created_at DESC")
            rules = db.execute(stmt, {"enabled": enabled}).fetchall()
        else:
            stmt = text("SELECT * FROM grasp_inject_rules ORDER BY created_at DESC")
            rules = db.execute(stmt).fetchall()
        
        results = []
        for r in rules:
            # r 是 sqlalchemy.engine.row.Row，字段是字符串
            # created_at/updated_at 是字符串，已经是 ISO 格式
            created_at = r.created_at if hasattr(r, 'created_at') else r[5]
            updated_at = r.updated_at if hasattr(r, 'updated_at') else r[6]
            
            # created_at/updated_at 是字符串，不需要 isoformat()
            created_at_str = str(created_at) if created_at else None
            updated_at_str = str(updated_at) if updated_at else None
            
            results.append(InjectRuleResponse(
                id=r.id if hasattr(r, 'id') else r[0],
                name=r.name if hasattr(r, 'name') else r[1],
                trigger_condition=r.trigger_condition if hasattr(r, 'trigger_condition') else r[2],
                target_kb=r.target_kb if hasattr(r, 'target_kb') else r[3],
                enabled=bool(r.enabled if hasattr(r, 'enabled') else r[4]),
                created_at=created_at_str,
                updated_at=updated_at_str,
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query inject rules: {str(e)}")

@router.get("/rules/{rule_id}", response_model=InjectRuleResponse)
def get_inject_rule(rule_id: str, db: Session = Depends(get_db)):
    """获取单个注入规则详情"""
    try:
        stmt = text("SELECT * FROM grasp_inject_rules WHERE id = :rule_id")
        rule = db.execute(stmt, {"rule_id": rule_id}).fetchone()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        created_at = rule.created_at if hasattr(rule, 'created_at') else rule[5]
        updated_at = rule.updated_at if hasattr(rule, 'updated_at') else rule[6]
        
        created_at_str = str(created_at) if created_at else None
        updated_at_str = str(updated_at) if updated_at else None
        
        return InjectRuleResponse(
            id=rule.id if hasattr(rule, 'id') else rule[0],
            name=rule.name if hasattr(rule, 'name') else rule[1],
            trigger_condition=rule.trigger_condition if hasattr(rule, 'trigger_condition') else rule[2],
            target_kb=rule.target_kb if hasattr(rule, 'target_kb') else rule[3],
            enabled=bool(rule.enabled if hasattr(rule, 'enabled') else rule[4]),
            created_at=created_at_str,
            updated_at=updated_at_str,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query inject rule: {str(e)}")

@router.post("/rules", response_model=InjectRuleResponse, status_code=status.HTTP_201_CREATED)
def create_inject_rule(request: InjectRuleCreate, db: Session = Depends(get_db)):
    """创建新的注入规则"""
    try:
        rule_id = str(uuid.uuid4())
        now = datetime.now()
        stmt = text("""
            INSERT INTO grasp_inject_rules (id, name, trigger_condition, target_kb, enabled, created_at, updated_at)
            VALUES (:id, :name, :trigger_condition, :target_kb, :enabled, :created_at, :updated_at)
        """)
        db.execute(stmt, {
            "id": rule_id,
            "name": request.name,
            "trigger_condition": request.trigger_condition,
            "target_kb": request.target_kb,
            "enabled": 1 if request.enabled else 0,
            "created_at": now,
            "updated_at": now,
        })
        db.commit()
        
        # 查询返回
        stmt = text("SELECT * FROM grasp_inject_rules WHERE id = :rule_id")
        rule = db.execute(stmt, {"rule_id": rule_id}).fetchone()
        
        created_at = rule.created_at if hasattr(rule, 'created_at') else rule[5]
        updated_at = rule.updated_at if hasattr(rule, 'updated_at') else rule[6]
        
        created_at_str = str(created_at) if created_at else None
        updated_at_str = str(updated_at) if updated_at else None
        
        return InjectRuleResponse(
            id=rule.id if hasattr(rule, 'id') else rule[0],
            name=rule.name if hasattr(rule, 'name') else rule[1],
            trigger_condition=rule.trigger_condition if hasattr(rule, 'trigger_condition') else rule[2],
            target_kb=rule.target_kb if hasattr(rule, 'target_kb') else rule[3],
            enabled=bool(rule.enabled if hasattr(rule, 'enabled') else rule[4]),
            created_at=created_at_str,
            updated_at=updated_at_str,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create inject rule: {str(e)}")

@router.patch("/rules/{rule_id}", response_model=InjectRuleResponse)
def update_inject_rule(rule_id: str, request: InjectRuleUpdate, db: Session = Depends(get_db)):
    """更新注入规则（部分更新）"""
    try:
        # 先检查是否存在
        stmt = text("SELECT * FROM grasp_inject_rules WHERE id = :rule_id")
        existing = db.execute(stmt, {"rule_id": rule_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 构建更新字段
        update_fields = {"updated_at": datetime.now()}
        if request.name is not None:
            update_fields["name"] = request.name
        if request.trigger_condition is not None:
            update_fields["trigger_condition"] = request.trigger_condition
        if request.target_kb is not None:
            update_fields["target_kb"] = request.target_kb
        if request.enabled is not None:
            update_fields["enabled"] = 1 if request.enabled else 0
        
        # 动态构建 UPDATE 语句
        set_clauses = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
        stmt = text(f"UPDATE grasp_inject_rules SET {set_clauses} WHERE id = :rule_id")
        
        update_params = {"rule_id": rule_id, **update_fields}
        db.execute(stmt, update_params)
        db.commit()
        
        # 查询返回
        stmt = text("SELECT * FROM grasp_inject_rules WHERE id = :rule_id")
        rule = db.execute(stmt, {"rule_id": rule_id}).fetchone()
        
        created_at = rule.created_at if hasattr(rule, 'created_at') else rule[5]
        updated_at = rule.updated_at if hasattr(rule, 'updated_at') else rule[6]
        
        created_at_str = str(created_at) if created_at else None
        updated_at_str = str(updated_at) if updated_at else None
        
        return InjectRuleResponse(
            id=rule.id if hasattr(rule, 'id') else rule[0],
            name=rule.name if hasattr(rule, 'name') else rule[1],
            trigger_condition=rule.trigger_condition if hasattr(rule, 'trigger_condition') else rule[2],
            target_kb=rule.target_kb if hasattr(rule, 'target_kb') else rule[3],
            enabled=bool(rule.enabled if hasattr(rule, 'enabled') else rule[4]),
            created_at=created_at_str,
            updated_at=updated_at_str,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update inject rule: {str(e)}")

@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inject_rule(rule_id: str, db: Session = Depends(get_db)):
    """删除注入规则"""
    try:
        stmt = text("DELETE FROM grasp_inject_rules WHERE id = :rule_id")
        result = db.execute(stmt, {"rule_id": rule_id})
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete inject rule: {str(e)}")

@router.get("/status", response_model=InjectStatusResponse)
def get_inject_status(db: Session = Depends(get_db)):
    """获取注入规则的启用状态摘要"""
    try:
        # 使用聚合查询统计启用/禁用规则数量
        stmt = text("""
            SELECT 
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count,
                SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) as disabled_count,
                COUNT(*) as total_count
            FROM grasp_inject_rules
        """)
        result = db.execute(stmt).fetchone()
        
        if result is None:
            return InjectStatusResponse(rules_enabled=0, rules_disabled=0, total_rules=0)
        
        return InjectStatusResponse(
            rules_enabled=result[0] or 0,
            rules_disabled=result[1] or 0,
            total_rules=result[2] or 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query inject status: {str(e)}")
