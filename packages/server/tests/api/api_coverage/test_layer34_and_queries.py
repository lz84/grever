"""
第 3 层 + 第 4 层 + 查询类接口测试

第 3 层：运行中交互 (HITL, Disputes, GrASP, Knowledge Injector)
第 4 层：监控与管理 (Scheduler, Traces, Admin)
查询类：无写入依赖的接口

对应测试用例：TC-L3-HI-01~10, TC-L3-D-01~09, TC-L3-GR-01~08,
TC-L3-KI-01~04, TC-L3-S-010~014, TC-L3-TR-01~05, TC-L3-ADM-01~06,
TC-L3-TM-01~02, TC-L3-ATT-01~02, TC-L3-ART-01~02, TC-L3-SEC-01,
TC-L3-DASH-01, TC-L3-SRCH-01, TC-L3-API-01~03
"""
import pytest
from conftest import gen_id


# ============================================================================
# 第 3 层：运行中交互
# ============================================================================

class TestLayer3_HITL:
    """TC-L3-HI-01~10: HITL 人机协同"""

    def test_01_pending_list(self, client):
        """TC-L3-HI-01: 获取待审批列表"""
        resp = client.get("/api/v1/human-input/pending")
        assert resp.status_code == 200

    def test_02_recent(self, client):
        """TC-L3-HI-02: 获取最近审批"""
        resp = client.get("/api/v1/human-input/recent")
        assert resp.status_code == 200

    def test_03_stats(self, client):
        """TC-L3-HI-03: 获取审批统计"""
        resp = client.get("/api/v1/human-input/stats")
        assert resp.status_code == 200

    def test_04_review_stats(self, client):
        """TC-L3-HI-04: 获取审核统计"""
        resp = client.get("/api/v1/human-input/review-stats")
        assert resp.status_code == 200

    def test_05_human_review_pending(self, client):
        """TC-L3-HI: 批量裁决列表"""
        resp = client.get("/api/v1/human-review/pending")
        assert resp.status_code == 200

    def test_06_human_review_stats(self, client):
        """TC-L3-HI: 审核统计"""
        resp = client.get("/api/v1/human-review/stats")
        assert resp.status_code == 200


class TestLayer3_Disputes:
    """TC-L3-D-01~09: 争议仲裁"""

    def test_01_list_disputes(self, client):
        """TC-L3-D-01: 获取争议列表"""
        resp = client.get("/api/v1/disputes")
        assert resp.status_code == 200

    def test_02_dispute_stats(self, client):
        """TC-L3-D-02: 获取争议统计"""
        resp = client.get("/api/v1/disputes/stats")
        assert resp.status_code == 200


class TestLayer3_GrASP:
    """TC-L3-GR-01~08: 认知引擎"""

    def test_01_cognition_list(self, client):
        """TC-L3-GR-03: 获取认知列表"""
        resp = client.get("/api/v1/grasp/cognition")
        assert resp.status_code == 200

    def test_02_knowledge_list(self, client):
        """TC-L3-GR-05: 获取知识列表"""
        resp = client.get("/api/v1/grasp/knowledge")
        assert resp.status_code == 200

    def test_03_graph(self, client):
        """TC-L3-GR-04: 获取知识图谱"""
        resp = client.get("/api/v1/grasp/graph")
        assert resp.status_code == 200

    def test_04_recommend(self, client):
        """TC-L3-GR-06: 获取认知推荐"""
        resp = client.post("/api/v1/grasp/recommend", json={})
        assert resp.status_code in (200, 400, 422)

    def test_05_inject_rules(self, client):
        """TC-L3-GR-07: 获取注入规则"""
        resp = client.get("/api/v1/grasp/inject/rules")
        assert resp.status_code == 200

    def test_06_inject_status(self, client):
        """TC-L3-GR-08: 获取注入状态"""
        resp = client.get("/api/v1/grasp/inject/status")
        assert resp.status_code == 200


class TestLayer3_KnowledgeInjector:
    """TC-L3-KI-01~04: 知识注入"""

    def test_01_task_result(self, client):
        """TC-L3-KI-01: 注入 Task 结果"""
        resp = client.post("/api/v1/knowledge-injector/task-result", json={})
        assert resp.status_code in (200, 400, 422)

    def test_02_workflow_result(self, client):
        """TC-L3-KI-02: 注入 Workflow 结果"""
        resp = client.post("/api/v1/knowledge-injector/workflow-result", json={})
        assert resp.status_code in (200, 400, 422)

    def test_03_dispute_result(self, client):
        """TC-L3-KI-03: 注入争议结果"""
        resp = client.post("/api/v1/knowledge-injector/dispute-result", json={})
        assert resp.status_code in (200, 400, 422)

    def test_04_status(self, client):
        """TC-L3-KI-04: 获取注入状态"""
        resp = client.get("/api/v1/knowledge-injector/status")
        assert resp.status_code == 200


# ============================================================================
# 第 4 层：监控与管理
# ============================================================================

class TestLayer4_Scheduler:
    """TC-L3-S-010~014: 调度器"""

    def test_01_scheduler_stats(self, client):
        """TC-L3-S-010: 获取调度器统计"""
        resp = client.get("/api/v1/scheduler/stats")
        assert resp.status_code == 200

    def test_02_scheduler_logs(self, client):
        """TC-L3-S-012: 获取调度日志"""
        resp = client.get("/api/v1/scheduler/logs")
        assert resp.status_code == 200


class TestLayer4_Traces:
    """TC-L3-TR-01~05: 执行追踪"""

    def test_01_list_traces(self, client):
        """TC-L3-TR-01: 获取追踪列表"""
        resp = client.get("/api/v1/traces")
        assert resp.status_code == 200


class TestLayer4_Timeout:
    """TC-L3-TM-01~02: 超时管理"""

    def test_01_timeout_check(self, client):
        """TC-L3-TM-01: 超时检查"""
        resp = client.get("/api/v1/timeout/check")
        assert resp.status_code == 200

    def test_02_timeout_config(self, client):
        """TC-L3-TM-02: 配置超时策略"""
        resp = client.post("/api/v1/timeout/config", json={})
        assert resp.status_code in (200, 400, 422)


class TestLayer4_Admin:
    """TC-L3-ADM-01~06: 管理面板"""

    def test_01_list_agents(self, client):
        """TC-L3-ADM-01: 管理面板 Agent 列表"""
        resp = client.get("/api/v1/admin/agents")
        assert resp.status_code == 200

    def test_02_list_tasks(self, client):
        """TC-L3-ADM-04: 管理面板 Task 列表"""
        resp = client.get("/api/v1/admin/tasks")
        assert resp.status_code == 200

    def test_03_cleanup_zombie(self, client):
        """TC-L3-ADM-06: 清理僵尸 Task"""
        resp = client.post("/api/v1/admin/cleanup/zombie-tasks")
        assert resp.status_code in (200, 400)


# ============================================================================
# 查询类接口（无写入依赖）
# ============================================================================

class TestQueryEndpoints:
    """查询类接口"""

    def test_01_security_alerts(self, client):
        """TC-L3-SEC-01: 安全告警查询"""
        resp = client.get("/api/v1/security/alerts")
        assert resp.status_code == 200

    def test_02_dashboard_stats(self, client):
        """TC-L3-DASH-01: 仪表板统计"""
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

    def test_03_search(self, client):
        """TC-L3-SRCH-01: 全局搜索"""
        resp = client.get("/api/v1/search")
        assert resp.status_code == 200

    def test_04_endpoints(self, client):
        """TC-L3-API-01: 端点列表"""
        resp = client.get("/api/v1/endpoints")
        assert resp.status_code == 200

    def test_05_status(self, client):
        """TC-L3-API-02: 系统健康检查"""
        resp = client.get("/api/v1/status")
        assert resp.status_code == 200

    def test_06_features(self, client):
        """TC-L3-API-03: 功能开关"""
        resp = client.get("/api/v1/features")
        assert resp.status_code == 200

    def test_07_events_stream(self, client):
        """TC-L3: 事件流"""
        resp = client.get("/api/v1/events/stream")
        assert resp.status_code == 200

    def test_08_artifacts(self, client):
        """TC-L3-ART-01: 产出物列表"""
        resp = client.get("/api/v1/artifacts")
        assert resp.status_code == 200

    def test_09_attachments(self, client):
        """TC-L3-ATT-02: 附件列表"""
        resp = client.get("/api/v1/attachments")
        assert resp.status_code == 200

    def test_10_reports(self, client, shared_data):
        """TC-L3-RPT-01: 报告获取"""
        resp = client.get("/api/v1/reports/test-workflow-id")
        assert resp.status_code in (200, 404)
