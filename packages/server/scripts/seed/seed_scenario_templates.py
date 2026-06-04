"""
Sprint 29-1.1: 填充 Scenario 模板数据

填充 3 个核心 Scenario 的 template_dag：
1. 地震救援总体预案 (Goal 级, 6 阶段)
2. 洪水应急总体预案 (Goal 级, 5 阶段)  
3. 危化品泄漏应急总体预案 (Goal 级, 5 阶段)
"""

import sys, json
sys.path.insert(0, r'D:\work\research\agents-nexus\packages\server\src')
from database.config import get_engine
from sqlalchemy import text

engine = get_engine()

# ============================================================================
# 1. 地震救援总体预案 (Goal 级, 6 阶段)
# ============================================================================

earthquake_dag = {
    "nodes": [
        {"id": "phase-1", "title": "应急响应启动", "description": "确认灾情等级，启动应急预案，成立指挥部", "type": "execution", "node_type": "execution"},
        {"id": "phase-2", "title": "专家会商研判", "description": "组织地震、地质、气象专家进行灾情研判", "type": "execution", "node_type": "execution"},
        {"id": "phase-3", "title": "综合抢险执行", "description": "开展人员搜救、伤员救治、基础设施抢修", "type": "execution", "node_type": "execution"},
        {"id": "phase-4", "title": "物资与人员调度", "description": "调配应急物资、安置受灾群众", "type": "execution", "node_type": "execution"},
        {"id": "phase-5", "title": "次生灾害防范", "description": "监测余震、堰塞湖、滑坡等次生灾害风险", "type": "execution", "node_type": "execution"},
        {"id": "phase-6", "title": "灾后恢复重建", "description": "评估损失，制定恢复重建计划", "type": "execution", "node_type": "execution"}
    ],
    "edges": [
        {"source": "phase-1", "target": "phase-2"},
        {"source": "phase-2", "target": "phase-3"},
        {"source": "phase-2", "target": "phase-4"},
        {"source": "phase-3", "target": "phase-5"},
        {"source": "phase-4", "target": "phase-5"},
        {"source": "phase-5", "target": "phase-6"}
    ]
}

# ============================================================================
# 2. 洪水应急总体预案 (Goal 级, 5 阶段)
# ============================================================================

flood_dag = {
    "nodes": [
        {"id": "phase-1", "title": "汛情监测预警", "description": "监测水位、雨量，发布预警信息", "type": "execution", "node_type": "execution"},
        {"id": "phase-2", "title": "应急响应启动", "description": "根据预警等级启动相应级别应急响应", "type": "execution", "node_type": "execution"},
        {"id": "phase-3", "title": "人员转移安置", "description": "组织危险区域人员转移，设置临时安置点", "type": "execution", "node_type": "execution"},
        {"id": "phase-4", "title": "抢险救灾执行", "description": "堤防加固、排涝抽水、救援被困人员", "type": "execution", "node_type": "execution"},
        {"id": "phase-5", "title": "灾后恢复", "description": "消杀防疫、基础设施修复、损失评估", "type": "execution", "node_type": "execution"}
    ],
    "edges": [
        {"source": "phase-1", "target": "phase-2"},
        {"source": "phase-2", "target": "phase-3"},
        {"source": "phase-2", "target": "phase-4"},
        {"source": "phase-3", "target": "phase-5"},
        {"source": "phase-4", "target": "phase-5"}
    ]
}

# ============================================================================
# 3. 危化品泄漏应急总体预案 (Goal 级, 5 阶段)
# ============================================================================

chemical_dag = {
    "nodes": [
        {"id": "phase-1", "title": "事故确认与报警", "description": "确认泄漏物质类型、数量、扩散范围", "type": "execution", "node_type": "execution"},
        {"id": "phase-2", "title": "应急响应启动", "description": "启动应急预案，划定警戒区域", "type": "execution", "node_type": "execution"},
        {"id": "phase-3", "title": "人员疏散与防护", "description": "疏散受影响区域人员，提供防护装备", "type": "execution", "node_type": "execution"},
        {"id": "phase-4", "title": "泄漏控制与处置", "description": "堵漏、围堵、收集泄漏物质", "type": "execution", "node_type": "execution"},
        {"id": "phase-5", "title": "环境监测与恢复", "description": "监测空气、水质污染，制定环境恢复方案", "type": "execution", "node_type": "execution"}
    ],
    "edges": [
        {"source": "phase-1", "target": "phase-2"},
        {"source": "phase-2", "target": "phase-3"},
        {"source": "phase-2", "target": "phase-4"},
        {"source": "phase-3", "target": "phase-5"},
        {"source": "phase-4", "target": "phase-5"}
    ]
}

# ============================================================================
# Agent requirements for each scenario
# ============================================================================

earthquake_agent_req = json.dumps([
    {"role": "搜救专家", "capabilities": ["search_and_rescue", "earthquake_response"], "min_agents": 1, "max_agents": 3},
    {"role": "医疗救护", "capabilities": ["medical_emergency", "triage"], "min_agents": 1, "max_agents": 5},
    {"role": "物资调度员", "capabilities": ["logistics", "resource_management"], "min_agents": 1, "max_agents": 2},
    {"role": "气象地质专家", "capabilities": ["meteorology", "geology", "risk_assessment"], "min_agents": 1, "max_agents": 2}
], ensure_ascii=False)

flood_agent_req = json.dumps([
    {"role": "水文监测员", "capabilities": ["hydrology", "water_level_monitoring"], "min_agents": 1, "max_agents": 2},
    {"role": "救援队员", "capabilities": ["water_rescue", "emergency_response"], "min_agents": 2, "max_agents": 5},
    {"role": "物资调度员", "capabilities": ["logistics", "resource_management"], "min_agents": 1, "max_agents": 2}
], ensure_ascii=False)

chemical_agent_req = json.dumps([
    {"role": "危化品专家", "capabilities": ["chemical_handling", "hazmat_response"], "min_agents": 1, "max_agents": 2},
    {"role": "环境监测员", "capabilities": ["environmental_monitoring", "air_quality"], "min_agents": 1, "max_agents": 2},
    {"role": "消防救援", "capabilities": ["firefighting", "emergency_response"], "min_agents": 2, "max_agents": 5}
], ensure_ascii=False)

# ============================================================================
# Insert/Update scenarios
# ============================================================================

scenarios = [
    {
        "id": "scenario-earthquake-001",
        "name": "地震救援总体预案",
        "category": "earthquake",
        "level": "goal",
        "template_dag": json.dumps(earthquake_dag, ensure_ascii=False),
        "agent_requirements": earthquake_agent_req,
        "description": "针对7.0级以上地震灾害的综合救援预案，涵盖从应急响应到灾后重建的完整流程。",
        "scenario_desc": "当地震监测系统检测到震级≥7.0时，自动触发本预案...",
        "trust_level": "high",
        "source": "manual",
        "usage_count": 42
    },
    {
        "id": "scenario-flood-001",
        "name": "洪水应急总体预案",
        "category": "flood",
        "level": "goal",
        "template_dag": json.dumps(flood_dag, ensure_ascii=False),
        "agent_requirements": flood_agent_req,
        "description": "针对洪涝灾害的应急预案，涵盖监测预警、人员转移、抢险救灾到灾后恢复。",
        "scenario_desc": "当水位监测超过警戒线或气象部门发布暴雨红色预警时触发...",
        "trust_level": "medium",
        "source": "manual",
        "usage_count": 18
    },
    {
        "id": "scenario-chemical-001",
        "name": "危化品泄漏应急总体预案",
        "category": "chemical",
        "level": "goal",
        "template_dag": json.dumps(chemical_dag, ensure_ascii=False),
        "agent_requirements": chemical_agent_req,
        "description": "针对危险化学品泄漏事故的应急预案，涵盖事故确认、人员疏散、泄漏控制到环境恢复。",
        "scenario_desc": "当化工园区监测系统检测到有毒气体浓度超标或收到泄漏报告时触发...",
        "trust_level": "medium",
        "source": "manual",
        "usage_count": 7
    }
]

with engine.begin() as conn:
    for s in scenarios:
        # Check if exists
        existing = conn.execute(text(
            "SELECT id FROM scenarios WHERE id = :id"
        ), {"id": s["id"]}).fetchone()
        
        if existing:
            conn.execute(text("""
                UPDATE scenarios SET 
                    name = :name, category = :category, level = :level,
                    template_dag = :template_dag,
                    agent_requirements = :agent_requirements,
                    description = :description, scenario_desc = :scenario_desc,
                    trust_level = :trust_level, source = :source,
                    usage_count = :usage_count, updated_at = datetime('now')
                WHERE id = :id
            """), s)
            print(f"  Updated: {s['id']} - {s['name']}")
        else:
            conn.execute(text("""
                INSERT INTO scenarios
                (id, name, category, status, version, description, scenario_desc,
                 level, template_dag, agent_requirements, trust_level, source,
                 usage_count, created_at, updated_at)
                VALUES
                (:id, :name, :category, 'active', 'v1.0', :description, :scenario_desc,
                 :level, :template_dag, :agent_requirements, :trust_level, :source,
                 :usage_count, datetime('now'), datetime('now'))
            """), s)
            print(f"  Created: {s['id']} - {s['name']}")

# Verify
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT id, name, level, 
               CASE WHEN template_dag IS NOT NULL THEN 'YES' ELSE 'NO' END as has_dag,
               CASE WHEN agent_requirements IS NOT NULL THEN 'YES' ELSE 'NO' END as has_agents
        FROM scenarios WHERE level = 'goal'
    """)).fetchall()
    
    print("\n=== Goal 级 Scenario 列表 ===")
    for r in rows:
        print(f"  {r[0]}: {r[1]} (level={r[2]}, has_dag={r[3]}, has_agents={r[4]})")

print("\n✅ Scenario 模板填充完成")
