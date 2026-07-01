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
from models import GraspInjectRule, GraspInjectLog

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
            rules = db.query(GraspInjectRule).filter(GraspInjectRule.enabled == enabled).order_by(GraspInjectRule.created_at.desc()).all()
        else:
            rules = db.query(GraspInjectRule).order_by(GraspInjectRule.created_at.desc()).all()
        
        results = []
        for r in rules:
            created_at = r.created_at.isoformat() if r.created_at else None
            updated_at = r.updated_at.isoformat() if r.updated_at else None
            
            results.append(InjectRuleResponse(
                id=r.id,
                name=r.name,
                trigger_condition=r.trigger_condition,
                target_kb=r.target_kb,
                enabled=bool(r.enabled),
                created_at=created_at,
                updated_at=updated_at,
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query inject rules: {str(e)}")

@router.get("/rules/logs")
def list_inject_logs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """获取注入日志列表（分页）"""
    try:
        offset = (page - 1) * page_size
        total = db.query(GraspInjectLog).count()
        logs = db.query(GraspInjectLog).order_by(GraspInjectLog.created_at.desc()).offset(offset).limit(page_size).all()
        results = []
        for l in logs:
            results.append({
                'id': l.id,
                'source': l.source,
                'type': l.type,
                'cognition_count': l.cognition_count,
                'status': l.status,
                'error_message': l.error_message,
                'extra': l.extra,
                'created_at': l.created_at.isoformat() if l.created_at else None,
            })
        return {'total': total, 'page': page, 'page_size': page_size, 'items': results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query inject logs: {str(e)}")

@router.get("/rules/{rule_id}", response_model=InjectRuleResponse)
def get_inject_rule(rule_id: str, db: Session = Depends(get_db)):
    """获取单个注入规则详情"""
    try:
        rule = db.query(GraspInjectRule).filter(GraspInjectRule.id == rule_id).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        created_at = rule.created_at.isoformat() if rule.created_at else None
        updated_at = rule.updated_at.isoformat() if rule.updated_at else None
        
        return InjectRuleResponse(
            id=rule.id,
            name=rule.name,
            trigger_condition=rule.trigger_condition,
            target_kb=rule.target_kb,
            enabled=bool(rule.enabled),
            created_at=created_at,
            updated_at=updated_at,
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
        
        # 创建新规则
        new_rule = GraspInjectRule(
            id=rule_id,
            name=request.name,
            trigger_condition=request.trigger_condition,
            target_kb=request.target_kb,
            enabled=1 if request.enabled else 0,
            created_at=now,
            updated_at=now,
        )
        db.add(new_rule)
        # db.commit() is handled automatically by get_db dependency
        
        # Refresh to get auto-generated fields
        db.refresh(new_rule)
        
        created_at = new_rule.created_at.isoformat() if new_rule.created_at else None
        updated_at = new_rule.updated_at.isoformat() if new_rule.updated_at else None
        
        return InjectRuleResponse(
            id=new_rule.id,
            name=new_rule.name,
            trigger_condition=new_rule.trigger_condition,
            target_kb=new_rule.target_kb,
            enabled=bool(new_rule.enabled),
            created_at=created_at,
            updated_at=updated_at,
        )
    except Exception as e:
        # db.rollback() is handled automatically by get_db dependency
        raise HTTPException(status_code=500, detail=f"Failed to create inject rule: {str(e)}")

@router.patch("/rules/{rule_id}", response_model=InjectRuleResponse)
def update_inject_rule(rule_id: str, request: InjectRuleUpdate, db: Session = Depends(get_db)):
    """更新注入规则（部分更新）"""
    try:
        # 先检查是否存在
        rule = db.query(GraspInjectRule).filter(GraspInjectRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 构建更新字段
        if request.name is not None:
            rule.name = request.name
        if request.trigger_condition is not None:
            rule.trigger_condition = request.trigger_condition
        if request.target_kb is not None:
            rule.target_kb = request.target_kb
        if request.enabled is not None:
            rule.enabled = 1 if request.enabled else 0
        rule.updated_at = datetime.now()
        
        # db.commit() is handled automatically by get_db dependency
        
        # Refresh to get updated values
        db.refresh(rule)
        
        created_at = rule.created_at.isoformat() if rule.created_at else None
        updated_at = rule.updated_at.isoformat() if rule.updated_at else None
        
        return InjectRuleResponse(
            id=rule.id,
            name=rule.name,
            trigger_condition=rule.trigger_condition,
            target_kb=rule.target_kb,
            enabled=bool(rule.enabled),
            created_at=created_at,
            updated_at=updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        # db.rollback() is handled automatically by get_db dependency
        raise HTTPException(status_code=500, detail=f"Failed to update inject rule: {str(e)}")

@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inject_rule(rule_id: str, db: Session = Depends(get_db)):
    """删除注入规则"""
    try:
        rule = db.query(GraspInjectRule).filter(GraspInjectRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        db.delete(rule)
        # db.commit() is handled automatically by get_db dependency
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        # db.rollback() is handled automatically by get_db dependency
        raise HTTPException(status_code=500, detail=f"Failed to delete inject rule: {str(e)}")

@router.get("/status", response_model=InjectStatusResponse)
def get_inject_status(db: Session = Depends(get_db)):
    """获取注入规则的启用状态摘要"""
    try:
        # 使用聚合查询统计启用/禁用规则数量
        enabled_count = db.query(GraspInjectRule).filter(GraspInjectRule.enabled == 1).count()
        disabled_count = db.query(GraspInjectRule).filter(GraspInjectRule.enabled == 0).count()
        total_count = db.query(GraspInjectRule).count()
        
        return InjectStatusResponse(
            rules_enabled=enabled_count,
            rules_disabled=disabled_count,
            total_rules=total_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query inject status: {str(e)}")
