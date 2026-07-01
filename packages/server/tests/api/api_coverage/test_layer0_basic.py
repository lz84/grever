"""
第 0 层：基础资源初始化测试

无依赖，首先执行。
- Agent 注册/心跳
- 系统设置读写
- 行业标签/包/技能查询
- MCP 服务器查询

对应测试用例：TC-L3-A-020~025, TC-L3-SET-01~04, TC-L3-IT-01~06,
TC-L3-IP-01~04, TC-L3-SK-01~05, TC-L3-MCP-01~03
"""
import pytest
from conftest import gen_id, default_capability_tags


class TestLayer0_Agents:
    """TC-L3-A-020~025: Agent 生命周期"""

    def test_01_register_agent(self, client, shared_data):
        """TC-L3-A-020: 注册新 Agent"""
        agent_id = gen_id("agent-l0")
        shared_data.agent_id = agent_id
        
        resp = client.post("/api/v1/agents", json={
            "id": agent_id,
            "name": "Layer0 Test Agent",
            "platform": "hermes",
            "capability_tags": default_capability_tags(),
        })
        assert resp.status_code in (200, 201, 409), f"Agent registration failed: {resp.text}"
        shared_data.agent_ids.append(agent_id)

    def test_02_agent_heartbeat(self, client, shared_data):
        """TC-L3-A-022: Agent 心跳上线"""
        if not shared_data.agent_id:
            pytest.skip("No agent registered")
        
        resp = client.post(f"/api/v1/agents/{shared_data.agent_id}/heartbeat", json={
            "load": 0.1,
            "status": "online",
        })
        assert resp.status_code == 200, f"Heartbeat failed: {resp.text}"

    def test_03_agents_health(self, client):
        """TC-L3-S-011: Agent 健康检查"""
        resp = client.get("/api/v1/scheduler/agents/health")
        assert resp.status_code == 200


class TestLayer0_Settings:
    """TC-L3-SET-01~04: 系统设置"""

    def test_01_list_settings(self, client):
        """TC-L3-SET-01: 获取所有设置"""
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200

    def test_02_list_models(self, client):
        """TC-L3-SET-02: 获取模型列表"""
        resp = client.get("/api/v1/settings/models")
        assert resp.status_code == 200

    def test_03_list_sessions(self, client):
        """TC-L3-SET-03: 获取会话列表"""
        resp = client.get("/api/v1/settings/sessions")
        assert resp.status_code == 200


class TestLayer0_IndustryTags:
    """TC-L3-IT-01~06: 行业标签"""

    def test_01_list_tags(self, client):
        """TC-L3-IT-01: 获取标签列表"""
        resp = client.get("/api/v1/industry-tags")
        assert resp.status_code == 200

    def test_02_list_industries(self, client):
        """TC-L3-IT-03: 获取行业列表"""
        resp = client.get("/api/v1/industry-tags/_industries")
        assert resp.status_code == 200

    def test_03_tag_stats(self, client):
        """TC-L3-IT-04: 获取标签统计"""
        resp = client.get("/api/v1/industry-tags/_stats")
        assert resp.status_code == 200


class TestLayer0_IndustryPacks:
    """TC-L3-IP-01~04: 行业包"""

    def test_01_list_packs(self, client, shared_data):
        """TC-L3-IP-01: 获取行业包列表"""
        resp = client.get("/api/v1/industry-packs")
        assert resp.status_code == 200
        data = resp.json()
        packs = data if isinstance(data, list) else data.get("packs", [])
        if packs:
            shared_data.pack_id = packs[0].get("id")

    def test_02_list_versions(self, client, shared_data):
        """TC-L3-IP: 获取版本历史"""
        if not shared_data.pack_id:
            pytest.skip("No pack available")
        resp = client.get(f"/api/v1/industry-packs/{shared_data.pack_id}/versions")
        assert resp.status_code == 200


class TestLayer0_Skills:
    """TC-L3-SK-01~05: 技能管理"""

    def test_01_list_skills(self, client, shared_data):
        """TC-L3-SK-01: 获取技能列表"""
        resp = client.get("/api/v1/skills")
        assert resp.status_code == 200
        data = resp.json()
        skills = data if isinstance(data, list) else data.get("skills", data.get("items", []))
        if skills:
            shared_data.skill_id = skills[0].get("id")

    def test_02_get_skill(self, client, shared_data):
        """TC-L3-SK-02: 获取技能详情"""
        if not shared_data.skill_id:
            pytest.skip("No skill available")
        resp = client.get(f"/api/v1/skills/{shared_data.skill_id}")
        assert resp.status_code == 200


class TestLayer0_MCP:
    """TC-L3-MCP-01~03: MCP 服务器"""

    def test_01_list_mcp_servers(self, client):
        """TC-L3-MCP-01: 获取 MCP 服务器列表"""
        resp = client.get("/api/v1/mcp-servers")
        assert resp.status_code == 200

    def test_02_list_mcp_all(self, client):
        """TC-L3-MCP-02: MCP 统一列表"""
        resp = client.get("/api/v1/mcp")
        assert resp.status_code == 200
