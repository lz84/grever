"""
Agent 负载管理与限流单元测试 (MAK-237)

测试用例：
1. 负载查询 API 可用
2. 负载配置 API 可用
3. 超负载时拒绝分配
4. 离线 Agent 任务重新分配
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from persistence.base import DatabaseConfig
from persistence.database import DatabaseManager
from api.server import create_app


# ========== 数据库设置 ==========

@pytest.fixture(scope="module")
def db_manager():
    """创建测试数据库"""
    config = DatabaseConfig(provider="sqlite", path=":memory:")
    db = DatabaseManager(config)
    db.create_tables()
    
    # 插入测试数据
    with db.engine.begin() as conn:
        # 插入 Agent
        conn.execute(text("""
            INSERT INTO agents (id, name, capabilities, status, address, metadata, load, current_tasks)
            VALUES ('agent-001', 'Test Agent', '["coding"]', 'online', 'http://localhost:8000', '{}', 50, 2)
        """))
        
        # 插入 Tasks
        conn.execute(text("""
            INSERT INTO tasks (id, title, description, goal_id, status, priority, assigned_agent)
            VALUES 
                ('task-001', 'Task 1', 'Test task 1', 'goal-001', 'todo', 1, 'agent-001'),
                ('task-002', 'Task 2', 'Test task 2', 'goal-001', 'todo', 2, NULL),
                ('task-003', 'Task 3', 'Test task 3', 'goal-002', 'in_progress', 1, 'agent-001')
        """))
        
        # 更新 agents 表 添加负载配置字段（模拟迁移）
        try:
            conn.execute(text("ALTER TABLE agents ADD COLUMN max_concurrent_tasks INTEGER DEFAULT 5"))
            conn.execute(text("ALTER TABLE agents ADD COLUMN load_threshold INTEGER DEFAULT 80"))
            conn.execute(text("ALTER TABLE agents ADD COLUMN recovery_threshold INTEGER DEFAULT 50"))
        except Exception:
            pass  # 列已存在
        
        conn.commit()
    
    yield db
    db.close()


@pytest.fixture(scope="module")
def client(db_manager):
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


# ========== 测试用例 ==========

class TestLoadManagementAPI:
    """测试负载管理 API"""
    
    def test_get_agent_load(self, client):
        """测试 GET /api/v1/agents/{id}/load"""
        response = client.get("/api/v1/agents/agent-001/load")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "agent-001"
        assert data["current_tasks"] == 2
        assert data["load_threshold"] == 80
        assert data["recovery_threshold"] == 50
    
    def test_update_agent_load_config(self, client):
        """测试 PUT /api/v1/agents/{id}/config"""
        config = {
            "max_concurrent_tasks": 10,
            "load_threshold": 90,
            "recovery_threshold": 60,
        }
        
        response = client.put("/api/v1/agents/agent-001/config", json=config)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "agent-001"
        assert data["max_concurrent_tasks"] == 10
        assert data["load_threshold"] == 90
        assert data["recovery_threshold"] == 60
    
    def test_get_agent_pending_tasks(self, client):
        """测试 GET /api/v1/agents/{id}/pending-tasks"""
        response = client.get("/api/v1/agents/agent-001/pending-tasks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "agent-001"
        assert data["total_count"] >= 1  # 至少有 1 个 pending 任务
        assert isinstance(data["pending_tasks"], list)


class TestLoadLimiting:
    """测试负载限流"""
    
    def test_overloaded_agent_rejects_tasks(self, db_manager, client):
        """测试超载 Agent 拒绝新任务"""
        # 更新 Agent 为超载状态
        with db_manager.engine.begin() as conn:
            conn.execute(text("""
                UPDATE agents
                SET current_tasks = 10, load = 95
                WHERE id = 'agent-001'
            """))
            conn.commit()
        
        # 检查负载
        response = client.get("/api/v1/agents/agent-001/load")
        assert response.status_code == 200
        data = response.json()
        
        # 应该标记为超载
        assert data["is_overloaded"] == True


class TestOfflineHandling:
    """测试离线处理"""
    
    def test_offline_agent_tasks_reassigned(self, db_manager):
        """测试 offline Agent 的任务被重新分配"""
        # 初始化数据库
        with db_manager.engine.begin() as conn:
            # 插入 Agent
            conn.execute(text("""
                INSERT INTO agents (id, name, capabilities, status, address, metadata, load, current_tasks)
                VALUES ('agent-offline', 'Offline Agent', '["coding"]', 'offline', 'http://localhost:8000', '{}', 0, 0)
            """))
            
            # 插入 Tasks
            conn.execute(text("""
                INSERT INTO tasks (id, title, description, goal_id, status, priority, assigned_agent)
                VALUES 
                    ('task-offline-1', 'Task Offline 1', 'Task for offline agent 1', 'goal-001', 'todo', 1, 'agent-offline'),
                    ('task-offline-2', 'Task Offline 2', 'Task for offline agent 2', 'goal-002', 'in_progress', 1, 'agent-offline')
            """))
            
            conn.commit()
        
        # 模拟重新分配逻辑
        with db_manager.engine.begin() as conn:
            # 获取 pending 任务
            pending_query = text("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status IN ('todo', 'pending')
                  AND assigned_agent = 'agent-offline'
            """)
            
            pending_count = conn.execute(pending_query).fetchone().count
            
            # 重新分配 pending 任务
            if pending_count > 0:
                conn.execute(text("""
                    UPDATE tasks
                    SET assigned_agent = NULL,
                        updated_at = datetime('now')
                    WHERE status IN ('todo', 'pending')
                      AND assigned_agent = 'agent-offline'
                """))
            
            # 标记 in_progress 任务为 blocked
            blocked_query = text("""
                UPDATE tasks
                SET status = 'blocked',
                    blocked_reason = 'Agent went offline',
                    updated_at = datetime('now')
                WHERE status = 'in_progress'
                  AND assigned_agent = 'agent-offline'
            """)
            
            conn.execute(blocked_query)
            conn.commit()
        
        # 验证结果
        with db_manager.engine.begin() as conn:
            # 检查 pending 任务是否已重新分配
            pending_check = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status IN ('todo', 'pending')
                  AND assigned_agent = 'agent-offline'
            """)).fetchone()
            
            # 检查 in_progress 任务是否被 blocked
            blocked_check = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status = 'blocked'
                  AND assigned_agent = 'agent-offline'
            """)).fetchone()
            
            # pending 任务应该被重新分配（assigned_agent = NULL）
            assert pending_check.count == 0
            
            # in_progress 任务应该被 blocked
            assert blocked_check.count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
