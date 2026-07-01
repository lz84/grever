"""能力库 API — GET /api/v1/capabilities"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Query
from sqlalchemy import Table, MetaData
from persistence.database import DatabaseManager
from persistence.base import DatabaseConfig

router = APIRouter(prefix="/api/v1/capabilities", tags=["能力库"])

DB_PATH = str(Path(__file__).resolve().parents[4] / "data" / "reins.db")

def get_db():
    config = DatabaseConfig(provider="sqlite", path=DB_PATH)
    db = DatabaseManager(config)
    try:
        yield db
    finally:
        db.close()

@router.get("")
async def list_capabilities(
    category: str = Query(None, description="按分类筛选"),
    status: str = Query(None, description="按状态筛选"),
    limit: int = Query(100, ge=1, le=500),
):
    """获取能力库列表"""
    config = DatabaseConfig(provider="sqlite", path=DB_PATH)
    db = DatabaseManager(config)

    try:
        meta = MetaData()
        caps_tbl = Table("capabilities", meta, autoload_with=db.engine)
        with db.engine.connect() as conn:
            stmt = caps_tbl.select()
            if category:
                stmt = stmt.where(caps_tbl.c.category == category)
            if status:
                stmt = stmt.where(caps_tbl.c.status == status)
            stmt = stmt.order_by(caps_tbl.c.usage_count.desc()).limit(limit)

            result = conn.execute(stmt)
            capabilities = []
            for row in result.fetchall():
                row_dict = dict(row._mapping)
                if 'agents' in row_dict and isinstance(row_dict['agents'], str):
                    try:
                        row_dict['agents'] = json.loads(row_dict['agents'])
                    except (json.JSONDecodeError, TypeError):
                        row_dict['agents'] = []
                capabilities.append(row_dict)

            return {"capabilities": capabilities}
    finally:
        db.close()

@router.post("/seed")
async def seed_capabilities():
    """从 agents 表的 capability_tags 字段种子数据到 capabilities 表"""
    config = DatabaseConfig(provider="sqlite", path=DB_PATH)
    db = DatabaseManager(config)

    try:
        meta = MetaData()
        caps_tbl = Table("capabilities", meta, autoload_with=db.engine)
        agents_tbl = Table("agents", meta, autoload_with=db.engine)

        with db.engine.connect() as conn:
            agents_result = conn.execute(agents_tbl.select())
            rows = agents_result.fetchall()
            capability_stats = {}

            for row in rows:
                row_dict = dict(row._mapping)
                agent_id = row_dict['id']
                caps = []
                cap_data = row_dict.get('capability_tags')
                if cap_data:
                    try:
                        parsed = json.loads(cap_data) if isinstance(cap_data, str) else cap_data
                        if isinstance(parsed, dict):
                            for dim_tags in parsed.values():
                                if isinstance(dim_tags, list):
                                    caps.extend(dim_tags)
                        elif isinstance(parsed, list):
                            caps = parsed
                    except (json.JSONDecodeError, TypeError):
                        caps = []

                for cap in caps:
                    cap_name = cap.strip().lower()
                    if cap_name not in capability_stats:
                        capability_stats[cap_name] = {'count': 0, 'agents': []}
                    capability_stats[cap_name]['count'] += 1
                    if agent_id not in capability_stats[cap_name]['agents']:
                        capability_stats[cap_name]['agents'].append(agent_id)

            now = datetime.now()
            for cap_name, stats in capability_stats.items():
                category = _categorize(cap_name)
                agents_json = json.dumps(stats['agents'], ensure_ascii=False)

                # 先删除旧记录再插入（避免 unique 冲突）
                from sqlalchemy import delete
                conn.execute(delete(caps_tbl).where(caps_tbl.c.name == cap_name))
                conn.execute(
                    caps_tbl.insert().values(
                        id=str(uuid.uuid4()),
                        name=cap_name,
                        category=category,
                        description=f'Agent 能力：{cap_name}',
                        status='active',
                        agents=agents_json,
                        usage_count=stats['count'],
                        last_used=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
            conn.commit()

        return {"message": f"Seeded {len(capability_stats)} capabilities"}
    finally:
        db.close()

def _categorize(cap_name: str) -> str:
    """根据能力名称推断分类"""
    coding_kw = ['code', 'coding', 'program', 'develop', 'debug', 'test', 'deploy', 'refactor', 'api', 'sql', 'script']
    reasoning_kw = ['reason', 'think', 'plan', 'analyze', 'research', 'review']
    comm_kw = ['communicat', 'chat', 'message', 'email', 'notify', 'report']
    data_kw = ['data', 'analytics', 'visual', 'dash', 'metric', 'chart', 'statistic']

    for kw in coding_kw:
        if kw in cap_name:
            return 'code_generation'
    for kw in reasoning_kw:
        if kw in cap_name:
            return 'reasoning'
    for kw in comm_kw:
        if kw in cap_name:
            return 'communication'
    for kw in data_kw:
        if kw in cap_name:
            return 'analysis'
    return 'other'
