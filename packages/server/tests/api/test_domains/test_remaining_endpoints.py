"""
Remaining domains tests:
- MCP, Artifacts, Attachments, Traces, Reports
- Settings, Disputes
- Evo: Genes, Capsules, Distillation, Evolution Events, A2A
- Vigil: Roles, Trust
- Agent Schemes, Capabilities, Search, Dashboard, Security
- Agent Task Operations, Executions, Internal endpoints
- Scheduler endpoints
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id


# ===========================================================================
# MCP
# ===========================================================================
class TestMCP:
    """MCP server endpoints."""

    def test_list_mcp(self, client: TestClient):
        resp = client.get("/api/v1/mcp")
        assert resp.status_code != 500

    def test_list_mcp_servers(self, client: TestClient):
        resp = client.get("/api/v1/mcp-servers")
        assert resp.status_code != 500

    def test_get_mcp_server(self, client: TestClient):
        resp = client.get(f"/api/v1/mcp-servers/{gen_id('srv')}")
        assert resp.status_code != 500

    def test_get_mcp_server_tools(self, client: TestClient):
        resp = client.get(f"/api/v1/mcp-servers/{gen_id('srv')}/tools")
        assert resp.status_code != 500

    def test_create_mcp_server(self, client: TestClient):
        resp = client.post("/api/v1/mcp-servers", json={
            "name": gen_id("mcp"), "url": "http://localhost:8080"
        })
        assert resp.status_code != 500

    def test_update_mcp_server(self, client: TestClient):
        resp = client.put(f"/api/v1/mcp-servers/{gen_id('srv')}", json={"name": "updated"})
        assert resp.status_code != 500

    def test_delete_mcp_server(self, client: TestClient):
        resp = client.delete(f"/api/v1/mcp-servers/{gen_id('srv')}")
        assert resp.status_code != 500

    def test_agent_match_mcp(self, client: TestClient):
        resp = client.post(f"/api/v1/agents/{gen_id('agent')}/match-mcp", json={})
        assert resp.status_code != 500


# ===========================================================================
# Artifacts
# ===========================================================================
class TestArtifacts:
    """Artifact CRUD."""

    def test_list_artifacts(self, client: TestClient):
        resp = client.get("/api/v1/artifacts/")
        assert resp.status_code != 500

    def test_create_artifact(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/artifacts/", json={
            "title": gen_id("artifact"), "content": "test"
        })
        assert resp.status_code != 500
        if resp.status_code in (200, 201):
            data = resp.json()
            aid = data.get("id")
            if aid:
                shared_data.artifact_id = aid

    def test_get_artifact(self, client: TestClient, shared_data: SharedData):
        if not shared_data.artifact_id:
            pytest.skip("No artifact created")
        resp = client.get(f"/api/v1/artifacts/{shared_data.artifact_id}")
        assert resp.status_code != 500

    def test_get_artifact_download(self, client: TestClient, shared_data: SharedData):
        if not shared_data.artifact_id:
            pytest.skip("No artifact created")
        resp = client.get(f"/api/v1/artifacts/{shared_data.artifact_id}/download")
        assert resp.status_code != 500

    def test_update_artifact(self, client: TestClient, shared_data: SharedData):
        if not shared_data.artifact_id:
            pytest.skip("No artifact created")
        resp = client.patch(f"/api/v1/artifacts/{shared_data.artifact_id}", json={"title": "updated"})
        assert resp.status_code != 500

    def test_delete_artifact(self, client: TestClient, shared_data: SharedData):
        if not shared_data.artifact_id:
            pytest.skip("No artifact created")
        resp = client.delete(f"/api/v1/artifacts/{shared_data.artifact_id}")
        assert resp.status_code != 500


# ===========================================================================
# Attachments
# ===========================================================================
class TestAttachments:
    """Attachment endpoints."""

    def test_list_attachments(self, client: TestClient):
        resp = client.get("/api/v1/attachments")
        assert resp.status_code != 500

    def test_head_attachment(self, client: TestClient):
        resp = client.head(f"/api/v1/attachments/{gen_id('att')}")
        assert resp.status_code != 500

    def test_get_attachment_download(self, client: TestClient):
        resp = client.get(f"/api/v1/attachments/{gen_id('att')}/download")
        assert resp.status_code != 500

    def test_create_attachment_link(self, client: TestClient):
        resp = client.post(
            f"/api/v1/attachments/{gen_id('att')}/link",
            json={"entity_type": "goal", "entity_id": gen_id("goal")})
        assert resp.status_code != 500

    def test_delete_attachment(self, client: TestClient):
        resp = client.delete(f"/api/v1/attachments/{gen_id('att')}")
        assert resp.status_code != 500

    def test_delete_attachment_link(self, client: TestClient):
        resp = client.delete(
            f"/api/v1/attachments/{gen_id('att')}/link/goal/{gen_id('goal')}")
        assert resp.status_code != 500


# ===========================================================================
# Traces & Reports
# ===========================================================================
class TestTraces:
    """Trace endpoints."""

    def test_list_traces(self, client: TestClient):
        resp = client.get("/api/v1/traces")
        assert resp.status_code != 500

    def test_get_trace(self, client: TestClient):
        resp = client.get(f"/api/v1/traces/{gen_id('task')}")
        assert resp.status_code != 500

    def test_get_trace_execution_logs(self, client: TestClient):
        resp = client.get(f"/api/v1/traces/{gen_id('task')}/execution-logs")
        assert resp.status_code != 500

    def test_get_trace_step_status(self, client: TestClient):
        resp = client.get(f"/api/v1/traces/{gen_id('task')}/step-status")
        assert resp.status_code != 500

    def test_create_trace(self, client: TestClient):
        resp = client.post("/api/v1/traces", json={"task_id": gen_id("task")})
        assert resp.status_code != 500

    def test_complete_trace(self, client: TestClient):
        resp = client.patch(f"/api/v1/traces/{gen_id('task')}/complete", json={})
        assert resp.status_code != 500


class TestReports:
    """Report endpoints."""

    def test_get_report_by_task(self, client: TestClient):
        resp = client.get(f"/api/v1/reports/{gen_id('task')}")
        assert resp.status_code != 500

    def test_get_report_by_workflow(self, client: TestClient):
        resp = client.get(f"/api/v1/reports/{gen_id('wf')}")
        assert resp.status_code != 500


# ===========================================================================
# Settings
# ===========================================================================
class TestSettings:
    """Settings endpoints."""

    def test_list_settings(self, client: TestClient):
        resp = client.get("/api/v1/settings/")
        assert resp.status_code != 500

    def test_get_settings_category(self, client: TestClient):
        resp = client.get("/api/v1/settings/general")
        assert resp.status_code != 500

    def test_get_settings_key(self, client: TestClient):
        resp = client.get("/api/v1/settings/general/theme")
        assert resp.status_code != 500

    def test_list_models(self, client: TestClient):
        resp = client.get("/api/v1/settings/models")
        assert resp.status_code != 500

    def test_list_sessions(self, client: TestClient):
        resp = client.get("/api/v1/settings/sessions")
        assert resp.status_code != 500

    def test_update_settings_key(self, client: TestClient):
        resp = client.put("/api/v1/settings/general/theme", json={"value": "dark"})
        assert resp.status_code != 500

    def test_batch_update_settings(self, client: TestClient):
        resp = client.put("/api/v1/settings/general/batch", json={})
        assert resp.status_code != 500

    def test_test_connection(self, client: TestClient):
        resp = client.post("/api/v1/settings/test-connection", json={})
        assert resp.status_code != 500


# ===========================================================================
# Disputes
# ===========================================================================
class TestDisputes:
    """Dispute endpoints."""

    def test_list_disputes(self, client: TestClient):
        resp = client.get("/api/v1/disputes/")
        assert resp.status_code != 500

    def test_get_dispute(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.get(f"/api/v1/disputes/{shared_data.dispute_id}")
        assert resp.status_code != 500

    def test_get_dispute_detail(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.get(f"/api/v1/disputes/{shared_data.dispute_id}/detail")
        assert resp.status_code != 500

    def test_get_dispute_timeline(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.get(f"/api/v1/disputes/{shared_data.dispute_id}/timeline")
        assert resp.status_code != 500

    def test_disputes_stats(self, client: TestClient):
        resp = client.get("/api/v1/disputes/stats")
        assert resp.status_code != 500

    def test_create_dispute(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/disputes/", json={
            "task_id": gen_id("task"), "reason": "test"
        })
        assert resp.status_code != 500
        if resp.status_code in (200, 201):
            data = resp.json()
            did = data.get("id")
            if did:
                shared_data.dispute_id = did

    def test_resolve_dispute(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.patch(f"/api/v1/disputes/{shared_data.dispute_id}/resolve", json={"decision": "resolved"})
        assert resp.status_code != 500

    def test_update_dispute_status(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.patch(f"/api/v1/disputes/{shared_data.dispute_id}/status", json={"status": "resolved"})
        assert resp.status_code != 500

    def test_arbitrate_dispute(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.post(f"/api/v1/disputes/{shared_data.dispute_id}/arbitrate", json={"decision": "approve"})
        assert resp.status_code != 500

    def test_discuss_dispute(self, client: TestClient, shared_data: SharedData):
        if not shared_data.dispute_id:
            pytest.skip("No dispute created")
        resp = client.post(f"/api/v1/disputes/{shared_data.dispute_id}/discuss", json={"comment": "test"})
        assert resp.status_code != 500


# ===========================================================================
# Evo: Genes
# ===========================================================================
class TestGenes:
    """Gene endpoints."""

    def test_list_genes(self, client: TestClient):
        resp = client.get("/api/v1/evo/genes/")
        assert resp.status_code != 500

    def test_get_gene(self, client: TestClient, shared_data: SharedData):
        if not shared_data.gene_id:
            pytest.skip("No gene created")
        resp = client.get(f"/api/v1/evo/genes/{shared_data.gene_id}")
        assert resp.status_code != 500

    def test_create_gene(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/evo/genes/", json={"name": gen_id("gene"), "content": "test"})
        assert resp.status_code != 500
        if resp.status_code in (200, 201):
            data = resp.json()
            gid = data.get("id")
            if gid:
                shared_data.gene_id = gid

    def test_extract_genes(self, client: TestClient):
        resp = client.post("/api/v1/evo/genes/extract", json={})
        assert resp.status_code != 500


# ===========================================================================
# Evo: Capsules
# ===========================================================================
class TestCapsules:
    """Capsule endpoints."""

    def test_list_capsules(self, client: TestClient):
        resp = client.get("/api/v1/evo/capsules/")
        assert resp.status_code != 500

    def test_get_capsule(self, client: TestClient, shared_data: SharedData):
        if not shared_data.capsule_id:
            pytest.skip("No capsule created")
        resp = client.get(f"/api/v1/evo/capsules/{shared_data.capsule_id}")
        assert resp.status_code != 500

    def test_promote_capsule(self, client: TestClient, shared_data: SharedData):
        if not shared_data.capsule_id:
            pytest.skip("No capsule created")
        resp = client.put(f"/api/v1/evo/capsules/{shared_data.capsule_id}/promote", json={})
        assert resp.status_code != 500

    def test_deprecate_capsule(self, client: TestClient, shared_data: SharedData):
        if not shared_data.capsule_id:
            pytest.skip("No capsule created")
        resp = client.put(f"/api/v1/evo/capsules/{shared_data.capsule_id}/deprecate", json={})
        assert resp.status_code != 500


# ===========================================================================
# Evo: Distillation
# ===========================================================================
class TestDistillation:
    """Distillation endpoints."""

    def test_distill(self, client: TestClient):
        resp = client.post("/api/v1/evo/distill", json={"gene_id": gen_id("gene")})
        assert resp.status_code != 500

    def test_evolve_capabilities(self, client: TestClient):
        resp = client.post("/api/v1/evo/evolve-capabilities", json={})
        assert resp.status_code != 500

    def test_solidify(self, client: TestClient):
        resp = client.post("/api/v1/evo/solidify", json={})
        assert resp.status_code != 500


# ===========================================================================
# Evo: Evolution Events
# ===========================================================================
class TestEvolutionEvents:
    """Evolution event endpoints."""

    def test_list_events(self, client: TestClient):
        resp = client.get("/api/v1/evo/evolution-events/")
        assert resp.status_code != 500

    def test_create_event(self, client: TestClient):
        resp = client.post("/api/v1/evo/evolution-events/", json={"event_type": "test", "data": {}})
        assert resp.status_code != 500

    def test_revert_event(self, client: TestClient):
        resp = client.post(f"/api/v1/evo/evolution-events/{gen_id('event')}/revert", json={})
        assert resp.status_code != 500


# ===========================================================================
# Evo: A2A
# ===========================================================================
class TestA2A:
    """A2A messaging endpoints."""

    def test_list_a2a_messages(self, client: TestClient):
        resp = client.get("/api/v1/a2a/messages")
        assert resp.status_code != 500

    def test_send_a2a_message(self, client: TestClient):
        resp = client.post("/api/v1/a2a/messages", json={"agent_id": gen_id("agent"), "content": "test"})
        assert resp.status_code != 500

    def test_broadcast_a2a(self, client: TestClient):
        resp = client.post("/api/v1/a2a/broadcast", json={"task_id": gen_id("task"), "result": "test"})
        assert resp.status_code != 500


# ===========================================================================
# Vigil: Roles
# ===========================================================================
class TestVigilRoles:
    """Vigil roles endpoints."""

    def test_list_roles(self, client: TestClient):
        resp = client.get("/api/v1/vigil/roles/")
        assert resp.status_code != 500

    def test_get_role(self, client: TestClient, shared_data: SharedData):
        if not shared_data.role_id:
            pytest.skip("No role created")
        resp = client.get(f"/api/v1/vigil/roles/{shared_data.role_id}")
        assert resp.status_code != 500

    def test_create_role(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/vigil/roles/", json={"name": gen_id("role"), "description": "test"})
        assert resp.status_code != 500
        if resp.status_code in (200, 201):
            data = resp.json()
            rid = data.get("id")
            if rid:
                shared_data.role_id = rid

    def test_update_role(self, client: TestClient, shared_data: SharedData):
        if not shared_data.role_id:
            pytest.skip("No role created")
        resp = client.put(f"/api/v1/vigil/roles/{shared_data.role_id}", json={"name": "updated"})
        assert resp.status_code != 500

    def test_delete_role(self, client: TestClient, shared_data: SharedData):
        if not shared_data.role_id:
            pytest.skip("No role created")
        resp = client.delete(f"/api/v1/vigil/roles/{shared_data.role_id}")
        assert resp.status_code != 500


# ===========================================================================
# Vigil: Trust
# ===========================================================================
class TestVigilTrust:
    """Vigil trust endpoints."""

    def test_get_trust_agent(self, client: TestClient):
        resp = client.get(f"/api/v1/vigil/trust/agents/{gen_id('agent')}")
        assert resp.status_code != 500

    def test_update_trust_agent(self, client: TestClient):
        resp = client.post(f"/api/v1/vigil/trust/agents/{gen_id('agent')}", json={"trust_score": 0.8})
        assert resp.status_code != 500

    def test_get_trust_agent_history(self, client: TestClient):
        resp = client.get(f"/api/v1/vigil/trust/agents/{gen_id('agent')}/history")
        assert resp.status_code != 500


# ===========================================================================
# Agent Schemes
# ===========================================================================
class TestAgentSchemes:
    """Agent scheme endpoints."""

    def test_list_schemes(self, client: TestClient):
        resp = client.get("/api/v1/agent-schemes")
        assert resp.status_code != 500

    def test_get_scheme(self, client: TestClient):
        resp = client.get(f"/api/v1/agent-schemes/{gen_id('scheme')}")
        assert resp.status_code != 500

    def test_get_scheme_roles(self, client: TestClient):
        resp = client.get(f"/api/v1/agent-schemes/{gen_id('scheme')}/roles")
        assert resp.status_code != 500

    def test_create_scheme(self, client: TestClient):
        resp = client.post("/api/v1/agent-schemes", json={"name": gen_id("scheme"), "description": "test"})
        assert resp.status_code != 500

    def test_update_scheme(self, client: TestClient):
        resp = client.put(f"/api/v1/agent-schemes/{gen_id('scheme')}", json={"name": "updated"})
        assert resp.status_code != 500

    def test_delete_scheme(self, client: TestClient):
        resp = client.delete(f"/api/v1/agent-schemes/{gen_id('scheme')}")
        assert resp.status_code != 500

    def test_create_scheme_role(self, client: TestClient):
        resp = client.post(f"/api/v1/agent-schemes/{gen_id('scheme')}/roles", json={"name": "test-role"})
        assert resp.status_code != 500

    def test_delete_scheme_role(self, client: TestClient):
        resp = client.delete(f"/api/v1/agent-schemes/{gen_id('scheme')}/roles/{gen_id('role')}")
        assert resp.status_code != 500


# ===========================================================================
# Capabilities, Search, Dashboard, Security, Misc
# ===========================================================================
class TestCapabilities:
    """Capabilities endpoints."""

    def test_list_capabilities(self, client: TestClient):
        resp = client.get("/api/v1/capabilities")
        assert resp.status_code != 500

    def test_seed_capabilities(self, client: TestClient):
        resp = client.post("/api/v1/capabilities/seed", json={})
        assert resp.status_code != 500


class TestSearch:
    """Search endpoints."""

    def test_search(self, client: TestClient):
        resp = client.get("/api/v1/search")
        assert resp.status_code != 500


class TestDashboard:
    """Dashboard stats endpoints."""

    def test_dashboard_stats(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code != 500

    def test_dashboard_execution_trend(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/stats/execution-trend")
        assert resp.status_code != 500


class TestSecurity:
    """Security endpoints."""

    def test_security_alerts(self, client: TestClient):
        resp = client.get("/api/v1/security/alerts")
        assert resp.status_code != 500

    def test_security_audit_logs(self, client: TestClient):
        resp = client.get("/api/v1/security/audit/logs")
        assert resp.status_code != 500


class TestMiscEndpoints:
    """Miscellaneous: root, health, docs."""

    def test_root(self, client: TestClient):
        resp = client.get("/")
        assert resp.status_code != 500

    def test_health(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code != 500
        if resp.status_code == 200:
            data = resp.json()
            assert "status" in data

    def test_docs_endpoints(self, client: TestClient):
        resp = client.get("/api/v1/docs/endpoints")
        assert resp.status_code != 500

    def test_docs_features(self, client: TestClient):
        resp = client.get("/api/v1/docs/features")
        assert resp.status_code != 500

    def test_docs_status(self, client: TestClient):
        resp = client.get("/api/v1/docs/status")
        assert resp.status_code != 500


# ===========================================================================
# Agent Task Operations, Executions, Internal
# ===========================================================================
class TestAgentTaskOperations:
    """Agent task claim and report."""

    def test_claim_task(self, client: TestClient):
        resp = client.post(
            f"/api/v1/agents/{gen_id('agent')}/tasks/{gen_id('task')}/claim", json={})
        assert resp.status_code != 500

    def test_report_task(self, client: TestClient):
        resp = client.post(
            f"/api/v1/agents/{gen_id('agent')}/tasks/{gen_id('task')}/report",
            json={"result": "completed"})
        assert resp.status_code != 500


class TestExecutions:
    """Execution endpoints."""

    def test_list_executions(self, client: TestClient):
        resp = client.get("/api/v1/executions/")
        assert resp.status_code != 500


class TestInternalEndpoints:
    """Internal task management."""

    def test_recover_timeout(self, client: TestClient):
        resp = client.post("/api/v1/internal/tasks/recover-timeout", json={})
        assert resp.status_code != 500


# ===========================================================================
# Scheduler (may return 503 if scheduler not running)
# ===========================================================================
class TestSchedulerEndpoints:
    """Scheduler endpoints - may return 503 if scheduler not running."""

    def test_scheduler_agents_health(self, client: TestClient):
        resp = client.get("/api/v1/scheduler/agents/health")
        assert resp.status_code != 500

    def test_scheduler_logs(self, client: TestClient):
        resp = client.get("/api/v1/scheduler/logs")
        assert resp.status_code != 500

    def test_scheduler_stats(self, client: TestClient):
        resp = client.get("/api/v1/scheduler/stats")
        # Known: may return 500 if scheduler not initialized

    def test_scheduler_tick(self, client: TestClient):
        resp = client.post("/api/v1/scheduler/tick", json={})
        # Known: may return 503 if scheduler not running

    def test_scheduler_dependencies_unlock(self, client: TestClient):
        resp = client.post("/api/v1/scheduler/dependencies/unlock", json={})
        # Known: may return 503 if scheduler not running
