"""
Sprint 123 Phase 2+1+3+6: 软件开发演示数据种子脚本

灌入软件开发场景的演示数据：
- 3 个 Goals（电商重构/CI/CD/技术债清理）
- Projects 和 Tasks（外键正确关联）
- 5 个 Agents（PM/前后端/测试/DevOps）
- 2 个场景模板
"""

import os
import sys
from pathlib import Path

# 添加 src 到路径
scripts_dir = Path(__file__).resolve().parent
package_dir = scripts_dir.parent
project_root = package_dir.parent
src_dir = package_dir / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from sqlalchemy import select, func, text
from persistence.config import DatabaseConfig
from persistence.database import DatabaseManager


def get_db_path() -> Path:
    """从环境变量或默认路径获取数据库路径"""
    # 尝试从 .env 加载
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("SQLITE_PATH="):
                    val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        db_path = Path(val)
                        if db_path.is_absolute():
                            return db_path
                        return project_root / val

    # 默认路径
    return project_root / "data" / "reins.db"


def seed_database(db_path: Path):
    """灌入演示数据"""
    import sqlite3
    import uuid
    from datetime import datetime, timedelta

    def uid(prefix=''):
        return f"{prefix}{uuid.uuid4().hex[:8]}"

    now = datetime.utcnow()
    
    print(f"数据库路径: {db_path}")
    
    # 连接数据库
    os.environ["REINS_DB_PROVIDER"] = "sqlite"
    os.environ["REINS_DB_PATH"] = str(db_path)
    config = DatabaseConfig(provider="sqlite", path=str(db_path))
    manager = DatabaseManager(config)
    conn = manager.get_session()

    # 检查是否存在演示数据（幂等性）
    from persistence.tables import goals, projects, tasks, agents
    from sqlalchemy import select
    
    stmt = select(func.count()).select_from(goals)
    gc = conn.execute(stmt).scalar()
    
    if gc > 0:
        print(f"演示数据已存在 ({gc} goals)，跳过灌入")
        conn.close()
        manager.close()
        return

    print("开始灌入演示数据...")

    # 1. 插入 5 个 Agent
    agents_data = [
        ("agent-pm-001", "产品经理", '["product_management", "requirements", "roadmap"]', "online"),
        ("agent-dev-frontend-001", "前端开发", '["frontend", "react", "vue", "css"]', "online"),
        ("agent-dev-backend-001", "后端开发", '["backend", "python", "nodejs", "database"]', "online"),
        ("agent-qa-001", "测试工程师", '["qa", "testing", "automation", "ci"]', "online"),
        ("agent-devops-001", "DevOps 工程师", '["devops", "ci_cd", "docker", "k8s"]', "online"),
    ]

    from sqlalchemy import insert, select, text
    from sqlalchemy.sql import text

    for agent_id, name, capabilities, status in agents_data:
        # 检查是否存在
        result = conn.execute(
            text("SELECT COUNT(*) FROM agents WHERE id = :id"),
            {"id": agent_id}
        ).fetchone()
        
        if result[0] == 0:
            conn.execute(
                text("""
                    INSERT INTO agents 
                    (id, name, capability_tags, status, load, current_tasks, 
                     registered_at, last_heartbeat, trigger_mode, poll_interval_seconds)
                    VALUES (:id, :name, :capability_tags, :status, 0, 0, :created_at, :updated_at, 'sse', 10)
                """),
                {
                    "id": agent_id,
                    "name": name,
                    "capability_tags": capability_tags,
                    "status": status,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            )
            print(f"  Agent: {name}")

    # 2. 插入 Scenario Template
    scenario_templates = [
        ("scenario-agile-sprint-001", "敏捷开发迭代", "agile", "active", "agile"),
        ("scenario-bug-fix-001", "紧急 bug 修复", "hotfix", "active", "hotfix"),
    ]

    for sc_id, name, category, status, level in scenario_templates:
        result = conn.execute(
            text("SELECT COUNT(*) FROM scenarios WHERE id = :id"),
            {"id": sc_id}
        ).fetchone()
        
        if result[0] == 0:
            conn.execute(
                text("""
                    INSERT INTO scenarios 
                    (id, name, category, status, level, description, 
                     trust_level, source, usage_count, created_at, updated_at)
                    VALUES (:id, :name, :category, :status, :level, :desc,
                            'medium', 'manual', 0, :created_at, :updated_at)
                """),
                {
                    "id": sc_id,
                    "name": name,
                    "category": category,
                    "status": status,
                    "level": level,
                    "desc": f"{name}场景模板",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            )
            print(f"  Scenario Template: {name}")

    # 3. 插入 3 个 Goals（软件开发场景）
    goals_data = [
        {
            "id": "goal-ecommerce-001",
            "title": "电商系统 2.0 重构",
            "description": "升级电商平台到 2.0 版本，提升性能和用户体验",
            "status": "in_progress",
            "priority": "high",
            "progress": 0.3,
        },
        {
            "id": "goal-cicd-001",
            "title": "CI/CD 流水线搭建",
            "description": "构建完整的持续集成和持续部署流水线",
            "status": "planned",
            "priority": "medium",
            "progress": 0.0,
        },
        {
            "id": "goal-tech-debt-001",
            "title": "技术债清理 Sprint",
            "description": "集中清理历史技术债，提升代码质量",
            "status": "active",
            "priority": "low",
            "progress": 0.1,
        },
    ]

    for g in goals_data:
        result = conn.execute(
            text("SELECT COUNT(*) FROM goals WHERE id = :id"),
            {"id": g["id"]}
        ).fetchone()
        
        if result[0] == 0:
            conn.execute(
                text("""
                    INSERT INTO goals 
                    (id, title, description, status, priority, progress, 
                     mode, created_at, updated_at)
                    VALUES (:id, :title, :desc, :status, :priority, :progress,
                            'agentic', :created_at, :updated_at)
                """),
                {
                    "id": g["id"],
                    "title": g["title"],
                    "desc": g["description"],
                    "status": g["status"],
                    "priority": g["priority"],
                    "progress": g["progress"],
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            )
            print(f"  Goal: {g['title']} ({g['status']})")

    # 4. 为每个 Goal 创建 Projects 和 Tasks
    # Goal 1: 电商系统重构
    goal1_projects = [
        {
            "name": "前端重构",
            "desc": "重构前端代码，迁移到新框架",
            "tasks": [
                ("重构首页组件", "todo", 1, "agent-dev-frontend-001"),
                ("重构商品详情页", "todo", 1, "agent-dev-frontend-001"),
                ("重构购物车组件", "in_progress", 2, "agent-dev-frontend-001"),
                ("重构结算流程", "todo", 2, "agent-dev-frontend-001"),
                ("性能优化 - 首屏加载", "done", 1, "agent-dev-frontend-001"),
            ],
        },
        {
            "name": "后端 API 改造",
            "desc": "重构后端 API，提升性能",
            "tasks": [
                ("用户服务重构", "todo", 1, "agent-dev-backend-001"),
                ("商品服务重构", "in_progress", 1, "agent-dev-backend-001"),
                ("订单服务重构", "todo", 1, "agent-dev-backend-001"),
                ("支付服务对接", "todo", 2, "agent-dev-backend-001"),
                ("API 文档完善", "done", 2, "agent-dev-backend-001"),
            ],
        },
        {
            "name": "数据库迁移",
            "desc": "数据库结构优化和数据迁移",
            "tasks": [
                ("Schema 优化", "in_progress", 1, "agent-dev-backend-001"),
                ("数据迁移脚本", "todo", 1, "agent-dev-backend-001"),
                ("性能调优", "todo", 2, "agent-dev-backend-001"),
                ("备份恢复测试", "todo", 2, "agent-dev-backend-001"),
            ],
        },
        {
            "name": "测试覆盖",
            "desc": "提升自动化测试覆盖率",
            "tasks": [
                ("单元测试补全", "todo", 1, "agent-qa-001"),
                ("接口测试自动化", "in_progress", 1, "agent-qa-001"),
                ("E2E 测试搭建", "todo", 2, "agent-qa-001"),
                ("性能测试", "todo", 2, "agent-qa-001"),
            ],
        },
    ]

    # Goal 2: CI/CD 流水线搭建
    goal2_projects = [
        {
            "name": "GitHub Actions 配置",
            "desc": "配置完整的 CI/CD 流水线",
            "tasks": [
                ("基础流水线搭建", "todo", 1, "agent-devops-001"),
                ("测试环境配置", "in_progress", 1, "agent-devops-001"),
                ("部署环境配置", "todo", 1, "agent-devops-001"),
                ("环境变量管理", "todo", 2, "agent-devops-001"),
            ],
        },
        {
            "name": "Docker 镜像构建",
            "desc": "优化 Docker 镜像构建流程",
            "tasks": [
                ("Dockerfile 优化", "todo", 1, "agent-devops-001"),
                ("多阶段构建", "in_progress", 1, "agent-devops-001"),
                ("镜像缓存策略", "todo", 2, "agent-devops-001"),
                ("镜像安全扫描", "todo", 2, "agent-devops-001"),
            ],
        },
        {
            "name": "自动化测试集成",
            "desc": "集成自动化测试到流水线",
            "tasks": [
                ("测试框架集成", "todo", 1, "agent-qa-001"),
                ("覆盖率报告", "in_progress", 1, "agent-qa-001"),
                ("测试结果通知", "todo", 2, "agent-qa-001"),
            ],
        },
        {
            "name": "部署脚本",
            "desc": "编写自动化部署脚本",
            "tasks": [
                ("部署脚本编写", "todo", 1, "agent-devops-001"),
                ("滚动发布配置", "in_progress", 1, "agent-devops-001"),
                ("回滚机制", "todo", 2, "agent-devops-001"),
            ],
        },
    ]

    # Goal 3: 技术债清理 Sprint
    goal3_projects = [
        {
            "name": "TypeScript 严格模式",
            "desc": "迁移到 TypeScript 严格模式",
            "tasks": [
                ("tsconfig.json 更新", "todo", 1, "agent-dev-frontend-001"),
                ("代码类型修复", "in_progress", 1, "agent-dev-frontend-001"),
                ("类型定义补全", "todo", 2, "agent-dev-frontend-001"),
            ],
        },
        {
            "name": "组件库重构",
            "desc": "重构全局组件库",
            "tasks": [
                ("组件模块化", "todo", 1, "agent-dev-frontend-001"),
                ("样式统一", "in_progress", 1, "agent-dev-frontend-001"),
                ("文档完善", "todo", 2, "agent-dev-frontend-001"),
            ],
        },
        {
            "name": "API 响应时间优化",
            "desc": "优化 API 响应时间",
            "tasks": [
                ("性能分析", "todo", 1, "agent-dev-backend-001"),
                ("慢查询优化", "in_progress", 1, "agent-dev-backend-001"),
                ("缓存策略", "todo", 2, "agent-dev-backend-001"),
                ("压力测试", "todo", 2, "agent-dev-backend-001"),
            ],
        },
    ]

    all_projects = [
        ("goal-ecommerce-001", goal1_projects),
        ("goal-cicd-001", goal2_projects),
        ("goal-tech-debt-001", goal3_projects),
    ]

    total_tasks = 0
    for goal_id, projects in all_projects:
        for proj in projects:
            proj_id = uid('proj-')
            
            # 检查项目是否存在
            result = conn.execute(
                text("SELECT COUNT(*) FROM projects WHERE id = :id"),
                {"id": proj_id}
            ).fetchone()
            
            if result[0] == 0:
                conn.execute(
                    text("""
                        INSERT INTO projects 
                        (id, name, description, goal_id, status, created_at, updated_at)
                        VALUES (:id, :name, :desc, :goal_id, 'active', :created_at, :updated_at)
                    """),
                    {
                        "id": proj_id,
                        "name": proj["name"],
                        "desc": proj["desc"],
                        "goal_id": goal_id,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                )
                print(f"    Project: {proj['name']}")

                for task_title, task_status, priority, agent_id in proj["tasks"]:
                    task_id = uid('task-')
                    
                    conn.execute(
                        text("""
                            INSERT INTO tasks 
                            (id, title, description, project_id, goal_id, assigned_agent, 
                             status, priority, verifier_agent_id, needs_verification, 
                             created_at, updated_at)
                            VALUES (:id, :title, :desc, :project_id, :goal_id, :agent_id,
                                    :status, :priority, :verifier_agent_id, 1,
                                    :created_at, :updated_at)
                        """),
                        {
                            "id": task_id,
                            "title": task_title,
                            "desc": f"{task_title} - 详细描述",
                            "project_id": proj_id,
                            "goal_id": goal_id,
                            "agent_id": agent_id,
                            "status": task_status,
                            "priority": priority,
                            "verifier_agent_id": "agent-verifier-default",
                            "created_at": now.isoformat(),
                            "updated_at": now.isoformat(),
                        }
                    )
                    total_tasks += 1

                print(f"      -> {len(proj['tasks'])} tasks")

    # 提交事务
    conn.commit()

    # 5. 统计
    result = conn.execute(text("SELECT COUNT(*) FROM goals"))
    gc = result.fetchone()[0]
    result = conn.execute(text("SELECT COUNT(*) FROM projects"))
    pc = result.fetchone()[0]
    result = conn.execute(text("SELECT COUNT(*) FROM tasks"))
    tc = result.fetchone()[0]
    result = conn.execute(text("SELECT COUNT(*) FROM agents"))
    ac = result.fetchone()[0]

    print(f"\n演示数据统计:")
    print(f"  Goals: {gc}")
    print(f"  Projects: {pc}")
    print(f"  Tasks: {tc}")
    print(f"  Agents: {ac}")
    
    conn.close()
    manager.close()


if __name__ == "__main__":
    db_path = get_db_path()
    seed_database(db_path)
    print(f"\n演示数据灌入完成: {db_path}")
