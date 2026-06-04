"""
统一模型工厂 — 从 SQLAlchemy ORM 自动生成 Pydantic schema

ORM 是唯一权威。加一个 ORM 列 → API 的 Create/Update/Response 自动同步。
彻底消除 schemas/ 和 models/ 双写不同步的 bug。

用法：
    TaskCreate, TaskUpdate, TaskResponse = auto_schema(Task)
"""

from typing import Any, Optional, Set
from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import Column, DateTime, String, Text, Float, Integer, Boolean

def _get_python_type(col: Column) -> Any:
    """SQLAlchemy 列类型 → Python 类型"""
    if isinstance(col.type, (String, Text)):
        return str
    elif isinstance(col.type, DateTime):
        return str
    elif isinstance(col.type, Float):
        return float
    elif isinstance(col.type, Integer):
        return int
    elif isinstance(col.type, Boolean):
        return bool
    else:
        return Any

def auto_schema(
    orm_class: type,
    *,
    create_exclude: Optional[Set[str]] = None,
    update_exclude: Optional[Set[str]] = None,
    create_defaults: Optional[dict] = None,
) -> tuple:
    """
    从 SQLAlchemy ORM 类自动生成 (Create, Update, Response) Pydantic 模型。
    """
    columns = {c.name: c for c in orm_class.__table__.columns}

    # ── Create ──
    if create_exclude is None:
        create_exclude = {'id', 'created_at', 'updated_at'}
    create_defaults = create_defaults or {}

    create_fields = {}
    for name, col in columns.items():
        if name in create_exclude:
            continue
        py_type = _get_python_type(col)
        has_default = col.default is not None or name in create_defaults
        is_nullable = col.nullable

        if name in create_defaults:
            create_fields[name] = (Optional[py_type], create_defaults[name])
        elif has_default or is_nullable:
            create_fields[name] = (Optional[py_type], None)
        else:
            create_fields[name] = (py_type, ...)

    CreateSchema = create_model(f"{orm_class.__name__}Create", **create_fields)

    # ── Update ──
    if update_exclude is None:
        update_exclude = {'id'}

    update_fields = {}
    for name, col in columns.items():
        if name in update_exclude:
            continue
        py_type = _get_python_type(col)
        update_fields[name] = (Optional[py_type], None)

    UpdateSchema = create_model(f"{orm_class.__name__}Update", **update_fields)

    # ── Response: build a class manually with from_attributes=True ──
    response_fields = {}
    for name, col in columns.items():
        py_type = _get_python_type(col)
        response_fields[name] = (Optional[py_type], None)

    # Build Response class by subclassing a BaseModel with the config
    ResponseBase = BaseModel.model_validate

    class _ResponseBase(BaseModel):
        model_config = ConfigDict(from_attributes=True)

    # Use the base class approach that works with Pydantic v2
    annotations = {k: v[0] for k, v in response_fields.items()}

    # Create class dynamically
    ResponseSchema = type(
        f"{orm_class.__name__}Response",
        (_ResponseBase,),
        {
            '__annotations__': annotations,
            **{k: v[1] for k, v in response_fields.items()},
        },
    )

    return CreateSchema, UpdateSchema, ResponseSchema
