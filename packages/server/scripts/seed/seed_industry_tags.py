"""Seed script for industry capability tags

Sprint 93: 行业能力标签库基础设施
Inserts the chemical-emergency industry tag library (15 tags)
"""
import sys
import os
import json
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.config import get_engine
from sqlalchemy import text

ENGINE = get_engine()

TAGS = [
    # === business 维度 ===
    {
        "id": "biz:chemical-park-operations",
        "industry": "chemical-emergency",
        "tag_name": "化工园区运营",
        "tag_name_en": "Chemical Park Operations",
        "description": "了解化工园区的日常运营、设施管理、安全规范",
        "dimension": "business",
        "level": "basic",
        "prerequisites": [],
        "tools": [],
        "examples": ["了解园区布局、主要设施分布", "掌握园区安全管理规范"],
    },
    {
        "id": "biz:emergency-management",
        "industry": "chemical-emergency",
        "tag_name": "应急管理体系",
        "tag_name_en": "Emergency Management System",
        "description": "掌握应急管理体系框架、响应级别、组织架构",
        "dimension": "business",
        "level": "intermediate",
        "prerequisites": ["biz:chemical-park-operations"],
        "tools": [],
        "examples": ["理解Ⅰ/Ⅱ/Ⅲ级应急响应的触发条件", "掌握应急指挥体系架构"],
    },

    # === professional 维度 ===
    {
        "id": "chem:hazmat-identification",
        "industry": "chemical-emergency",
        "tag_name": "危化品识别",
        "tag_name_en": "Hazardous Material Identification",
        "description": "识别危险化学品类型、危害类别、处置方法",
        "dimension": "professional",
        "level": "intermediate",
        "prerequisites": ["chem:msds-parsing"],
        "tools": ["msds-parser", "hazmat-db"],
        "examples": ["识别泄漏物质为液氯，Ⅱ类危险品", "根据 MSDS 判断泄漏处置方案"],
    },
    {
        "id": "chem:diffusion-modeling",
        "industry": "chemical-emergency",
        "tag_name": "扩散建模",
        "tag_name_en": "Diffusion Modeling",
        "description": "建立危化品泄漏扩散模型，计算影响范围",
        "dimension": "professional",
        "level": "advanced",
        "prerequisites": ["chem:weather-analysis"],
        "tools": ["diffusion-calculator"],
        "examples": ["计算液氯泄漏后 30 分钟的扩散范围", "评估下风向 500 米内的影响区域"],
    },
    {
        "id": "chem:emergency-response-level",
        "industry": "chemical-emergency",
        "tag_name": "应急响应分级",
        "tag_name_en": "Emergency Response Level Assessment",
        "description": "根据泄漏量、物质类型、环境条件判断响应级别",
        "dimension": "professional",
        "level": "intermediate",
        "prerequisites": ["chem:hazmat-identification"],
        "tools": [],
        "examples": ["泄漏量 > 1 吨 → Ⅰ级响应", "泄漏量 0.1-1 吨 → Ⅱ级响应"],
    },
    {
        "id": "chem:evacuation-planning",
        "industry": "chemical-emergency",
        "tag_name": "疏散规划",
        "tag_name_en": "Evacuation Planning",
        "description": "制定人员疏散方案，确定疏散范围和路线",
        "dimension": "professional",
        "level": "advanced",
        "prerequisites": ["chem:diffusion-modeling", "chem:emergency-response-level"],
        "tools": [],
        "examples": ["根据扩散范围确定疏散半径", "规划最优疏散路线避开扩散区域"],
    },
    {
        "id": "chem:fire-suppression",
        "industry": "chemical-emergency",
        "tag_name": "火灾扑救",
        "tag_name_en": "Fire Suppression",
        "description": "化工火灾扑救策略、灭火剂选择、安全防护",
        "dimension": "professional",
        "level": "advanced",
        "prerequisites": [],
        "tools": [],
        "examples": ["液氯泄漏引发的火灾扑救策略", "选择合适的灭火剂（禁用直流水）"],
    },
    {
        "id": "chem:environmental-monitoring",
        "industry": "chemical-emergency",
        "tag_name": "环境监测",
        "tag_name_en": "Environmental Monitoring",
        "description": "事故期间和事故后的环境监测方案",
        "dimension": "professional",
        "level": "intermediate",
        "prerequisites": [],
        "tools": [],
        "examples": ["事故期间实时监测空气中有害气体浓度", "事故后评估土壤和水体污染情况"],
    },

    # === technical 维度 ===
    {
        "id": "chem:msds-parsing",
        "industry": "chemical-emergency",
        "tag_name": "MSDS 文档解析",
        "tag_name_en": "MSDS Document Parsing",
        "description": "解析化学品安全数据表（MSDS），提取关键安全信息",
        "dimension": "technical",
        "level": "basic",
        "prerequisites": [],
        "tools": ["msds-parser"],
        "examples": ["从 MSDS 中提取泄漏处置方法", "识别危化品的危险类别和防护要求"],
    },
    {
        "id": "chem:leak-rate-calculation",
        "industry": "chemical-emergency",
        "tag_name": "泄漏速率计算",
        "tag_name_en": "Leak Rate Calculation",
        "description": "根据储罐参数、泄漏孔径计算泄漏速率和泄漏量",
        "dimension": "technical",
        "level": "intermediate",
        "prerequisites": [],
        "tools": ["leak-calculator"],
        "examples": ["计算 10mm 孔径下液氯的泄漏速率", "估算 30 分钟内的总泄漏量"],
    },
    {
        "id": "chem:weather-analysis",
        "industry": "chemical-emergency",
        "tag_name": "气象数据分析",
        "tag_name_en": "Weather Data Analysis",
        "description": "分析风速、风向、温度、湿度等气象数据对泄漏扩散的影响",
        "dimension": "technical",
        "level": "intermediate",
        "prerequisites": [],
        "tools": ["weather-api"],
        "examples": ["根据实时风向判断扩散方向", "评估风速对扩散速度的影响"],
    },

    # === management 维度 ===
    {
        "id": "chem:incident-command",
        "industry": "chemical-emergency",
        "tag_name": "事故指挥",
        "tag_name_en": "Incident Command",
        "description": "事故现场指挥体系、决策流程、资源协调",
        "dimension": "management",
        "level": "advanced",
        "prerequisites": [],
        "tools": [],
        "examples": ["总指挥决策是否启动Ⅰ级响应", "现场指挥协调各专业组行动"],
    },
    {
        "id": "chem:resource-allocation",
        "industry": "chemical-emergency",
        "tag_name": "资源调配",
        "tag_name_en": "Resource Allocation",
        "description": "应急资源的调度与分配，包括人力、设备、物资",
        "dimension": "management",
        "level": "intermediate",
        "prerequisites": [],
        "tools": [],
        "examples": ["调配消防车辆到泄漏现场", "分配防护服和呼吸器给救援人员"],
    },
    {
        "id": "chem:multi-agency-coordination",
        "industry": "chemical-emergency",
        "tag_name": "多部门协调",
        "tag_name_en": "Multi-Agency Coordination",
        "description": "协调消防、环保、医疗、公安等多部门联合行动",
        "dimension": "management",
        "level": "advanced",
        "prerequisites": [],
        "tools": [],
        "examples": ["协调环保部门进行环境监测", "通知公安部门疏散周边居民"],
    },
]

SEED_PACK = {
    "id": "pack-chemical-emergency-v1",
    "name": "化工应急行业包",
    "industry": "chemical-emergency",
    "version": "1.0.0",
    "description": "化工园区应急响应全套场景模板，包含危化品泄漏、火灾、气体扩散等 12 个场景",
    "status": "draft",
}


def seed():
    now = int(time.time())
    inserted = 0
    skipped = 0

    with ENGINE.connect() as conn:
        # Insert tags
        for tag in TAGS:
            existing = conn.execute(
                text("SELECT id FROM industry_capability_tags WHERE id = :id"),
                {"id": tag["id"]}
            ).fetchone()
            if existing:
                skipped += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO industry_capability_tags 
                    (id, industry, tag_name, tag_name_en, description, dimension, level, 
                     prerequisites, tools, examples, status, created_at, updated_at)
                    VALUES (:id, :industry, :tag_name, :tag_name_en, :description, :dimension, 
                            :level, :prerequisites, :tools, :examples, :status, :created_at, :updated_at)
                """),
                {
                    **tag,
                    "prerequisites": json.dumps(tag["prerequisites"]),
                    "tools": json.dumps(tag["tools"]),
                    "examples": json.dumps(tag["examples"]),
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                }
            )
            inserted += 1

        # Insert seed pack
        existing_pack = conn.execute(
            text("SELECT id FROM industry_packs WHERE id = :id"),
            {"id": SEED_PACK["id"]}
        ).fetchone()
        if not existing_pack:
            conn.execute(
                text("""
                    INSERT INTO industry_packs 
                    (id, name, industry, version, description, tags_count, scenarios_count, 
                     skills_count, status, created_at, updated_at)
                    VALUES (:id, :name, :industry, :version, :description, :tags_count, 0, 0, 
                            :status, :created_at, :updated_at)
                """),
                {
                    **SEED_PACK,
                    "tags_count": len(TAGS),
                    "status": "draft",
                    "created_at": now,
                    "updated_at": now,
                }
            )

            # Link tags to pack
            for tag in TAGS:
                conn.execute(
                    text("""
                        INSERT OR IGNORE INTO industry_pack_contents (pack_id, content_type, content_id)
                        VALUES (:pack_id, 'tag', :content_id)
                    """),
                    {"pack_id": SEED_PACK["id"], "content_id": tag["id"]}
                )

        conn.commit()

    print(f"Seed complete: {inserted} tags inserted, {skipped} skipped")


if __name__ == "__main__":
    seed()
