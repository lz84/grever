"""
认证路由
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import hashlib

from .service import TokenService, TokenType
from .middleware import verify_token
from .models import Token
from shared.database.session import get_db_session

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


class TokenCreateRequest(BaseModel):
    """创建 Token 请求"""
    type: TokenType
    entity_id: str
    name: Optional[str] = None


class TokenCreateResponse(BaseModel):
    """创建 Token 响应"""
    token: str
    expires_at: str


class TokenRefreshRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """刷新 Token 响应"""
    token: str
    expires_at: str


@router.post("/token", response_model=TokenCreateResponse)
def create_token(
    request: TokenCreateRequest,
    db: Session = Depends(get_db_session)
):
    """
    创建新 Token

    - type: token 类型 (user/agent)
    - entity_id: 关联的实体 ID (user_id 或 agent_id)
    - name: token 名称（可选）
    """
    token_service = TokenService(db)
    
    try:
        raw_token, token_record = token_service.generate_token(
            token_type=request.type,
            entity_id=request.entity_id,
            name=request.name,
        )
        
        return TokenCreateResponse(
            token=raw_token,
            expires_at=token_record.expires_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db_session)
):
    """
    刷新 Token

    - refresh_token: 当前有效的 token
    """
    token_service = TokenService(db)
    
    new_token = token_service.refresh_token(
        refresh_token=request.refresh_token
    )
    
    if not new_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )
    
    # 重新查询新 token
    new_hash = hashlib.sha256(new_token.encode()).hexdigest()
    new_token_record = db.query(Token).filter(Token.hash == new_hash).first()
    
    return TokenRefreshResponse(
        token=new_token,
        expires_at=new_token_record.expires_at.isoformat() if new_token_record else "",
    )


@router.delete("/token/{token_id}")
def revoke_token(
    token_id: int,
    db: Session = Depends(get_db_session)
):
    """
    撤销 Token

    - token_id: 要撤销的 token ID
    """
    token_service = TokenService(db)
    
    success = token_service.revoke_token(token_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Token not found: {token_id}"
        )
    
    return {"message": f"Token {token_id} revoked successfully"}


# 导入 TokenService 用于 refresh 端点
from .service import TokenService as TokenService_


@router.get("/token", dependencies=[Depends(verify_token)])
def list_tokens(
    db: Session = Depends(get_db_session)
):
    """
    列出当前用户/Agent 的所有 Token
    """
    token_service = TokenService(db)
    token_record = verify_token.__wrapped__ if hasattr(verify_token, '__wrapped__') else None
    # 直接查询所有非撤销的 token
    tokens = db.query(Token).filter(Token.revoked == 0).all()
    return [t.to_dict() for t in tokens]
