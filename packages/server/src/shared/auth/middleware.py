"""
Token 验证中间件
"""

from fastapi import Request, Depends, HTTPException, Header
from typing import Optional
from sqlalchemy.orm import Session

from .service import TokenService
from shared.database.session import get_database_manager


async def verify_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_database_manager().get_session)
):
    """
    FastAPI 依赖项 - 验证 Bearer Token

    用法:
        @app.get("/protected")
        def protected_endpoint(token: Token = Depends(verify_token)):
            return {"user_id": token.user_id, "agent_id": token.agent_id}

    Args:
        authorization: Authorization header (Bearer <token>)
        db: 数据库会话

    Returns:
        Token: 验证通过的 Token 对象

    Raises:
        HTTPException(401): Token 无效或已过期
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 解析 Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = parts[1]

    # 验证 Token
    token_service = TokenService(db)
    token_record = token_service.verify_token(token)

    if not token_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return token_record


def require_auth(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_database_manager().get_session)
):
    """
    强制认证依赖（与 verify_token 相同，仅语义更明确）

    用法:
        @app.post("/goal")
        def create_goal(
            goal: GoalCreate,
            token: Token = Depends(require_auth)
        ):
            return {"user_id": token.user_id}
    """
    return verify_token(authorization, db)


def optional_auth(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_database_manager().get_session)
) -> Optional[object]:
    """
    可选认证依赖

    用法:
        @app.get("/public-api")
        def public_endpoint(token: Optional[Token] = Depends(optional_auth)):
            user_id = token.user_id if token else None
            return {"user_id": user_id}
    """
    if not authorization:
        return None

    try:
        return verify_token(authorization, db)
    except HTTPException:
        return None
