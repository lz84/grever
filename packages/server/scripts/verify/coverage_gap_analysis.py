#!/usr/bin/env python
"""Analyze test coverage gaps by comparing all endpoints vs existing test files."""
import re
from pathlib import Path

# All endpoints from OpenAPI schema (manually extracted)
ALL_ENDPOINTS = []
endpoint_text = """DELETE /api/v1/agent-schemes/{scheme_id}
DELETE /api/v1/agent-schemes/{scheme_id}/roles/{role_id}
DELETE /api/v1/agents/{agent_id}
DELETE /api/v1/artifacts/{artifact_id}
DELETE /api/v1/attachments/{id}
DELETE /api/v1/attachments/{id}/link/{entity_type}/{entity_id}
DELETE /api/v1/goals/{goal_id}
DELETE /api/v1/grasp/{cognition_id}
DELETE /api/v1/grasp/cognition/{cognition_id}
DELETE /api/v1/grasp/inject/rules/{rule_id}
DELETE /api/v1/industry-packs/{pack_id}
DELETE /api/v1/knowledge/{entry_id}
DELETE /api/v1/mcp-servers/{server_id}
DELETE /api/v1/pack-skills/{skill_id}
DELETE /api/v1/projects/{project_id}
DELETE /api/v1/scenarios/{scenario_id}
DELETE /api/v1/scenarios/{scenario_id}/projects/{project_id}
DELETE /api/v1/scenarios/{scenario_id}/tasks/{task_id}
DELETE /api/v1/solutions/{solution_id}
DELETE /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}/attachments/{attachment_id}
DELETE /api/v1/tasks/{task_id}/comments/{comment_id}
DELETE /api/v1/tasks/{task_id}/labels/{label_id}
DELETE /api/v1/tasks/{task_id}/sub-issues/{relation_id}
DELETE /api/v1/vigil/roles/{role_id}
DELETE /api/v1/workflows/{workflow_id}/dag/edges/{source}/{target}
DELETE /api/v1/workflows/{workflow_id}/dag/nodes/{node_id}
GET /api/v1/a2a/messages
GET /api/v1/agent-platforms
GET /api/v1/agent-platforms/{platform_type}/registration-schema
GET /api/v1/agent-schemes
GET /api/v1/agent-schemes/{scheme_id}
GET /api/v1/agent-schemes/{scheme_id}/roles
GET /api/v1/agents
GET /api/v1/agents/{agent_id}
GET /api/v1/agents/{agent_id}/execution-logs
GET /api/v1/agents/{agent_id}/heartbeat_logs
GET /api/v1/agents/{agent_id}/load
GET /api/v1/agents/{agent_id}/pending-tasks
GET /api/v1/agents/{agent_id}/tag-recommendations
GET /api/v1/agents/online
GET /api/v1/agents/stats
GET /api/v1/artifacts/
GET /api/v1/artifacts/{artifact_id}
GET /api/v1/artifacts/{artifact_id}/download
GET /api/v1/attachments
GET /api/v1/attachments/{id}/download
GET /api/v1/capabilities
GET /api/v1/dashboard/stats
GET /api/v1/dashboard/stats/execution-trend
GET /api/v1/discover
GET /api/v1/discover/{agent_id}
GET /api/v1/disputes/
GET /api/v1/disputes/{dispute_id}
GET /api/v1/disputes/{dispute_id}/detail
GET /api/v1/disputes/{dispute_id}/timeline
GET /api/v1/disputes/stats
GET /api/v1/docs/endpoints
GET /api/v1/docs/features
GET /api/v1/docs/status
GET /api/v1/evo/capsules/
GET /api/v1/evo/capsules/{capsule_id}
GET /api/v1/evo/evolution-events/
GET /api/v1/evo/genes/
GET /api/v1/evo/genes/{gene_id}
GET /api/v1/executions/
GET /api/v1/goals
GET /api/v1/goals/
GET /api/v1/goals/{goal_id}
GET /api/v1/goals/{goal_id}/constraints
GET /api/v1/goals/{goal_id}/iteration-status
GET /api/v1/goals/{goal_id}/iterations
GET /api/v1/goals/{goal_id}/tree
GET /api/v1/goals/active
GET /api/v1/grasp/active-backend
GET /api/v1/grasp/backends
GET /api/v1/grasp/cognition-assessment/{agent_id}
GET /api/v1/grasp/cognition/{cognition_id}
GET /api/v1/grasp/cognitions
GET /api/v1/grasp/graph
GET /api/v1/grasp/inject/rules
GET /api/v1/grasp/inject/rules/{rule_id}
GET /api/v1/grasp/inject/rules/logs
GET /api/v1/grasp/inject/status
GET /api/v1/grasp/knowledge
GET /api/v1/health
GET /api/v1/human-input/{input_id}
GET /api/v1/human-input/pending
GET /api/v1/human-input/recent
GET /api/v1/human-input/review-stats
GET /api/v1/human-input/scenario/{scenario_id}/pending
GET /api/v1/human-input/stats
GET /api/v1/human-input/task/{task_id}
GET /api/v1/human-review/pending
GET /api/v1/human-review/stats
GET /api/v1/industry-packs
GET /api/v1/industry-packs/{pack_a}/diff/{pack_b}
GET /api/v1/industry-packs/{pack_id}
GET /api/v1/industry-packs/{pack_id}/versions
GET /api/v1/industry-tags/
GET /api/v1/industry-tags/_by-industry/{industry}
GET /api/v1/industry-tags/_industries
GET /api/v1/industry-tags/_stats
GET /api/v1/industry-tags/agent-tag-recommend
GET /api/v1/industry-tags/agent-tags
GET /api/v1/knowledge
GET /api/v1/knowledge/{entry_id}
GET /api/v1/mcp
GET /api/v1/mcp-servers
GET /api/v1/mcp-servers/{server_id}
GET /api/v1/mcp-servers/{server_id}/tools
GET /api/v1/pack-skills
GET /api/v1/pack-skills/{skill_id}
GET /api/v1/pack-skills/by-pack/{pack_id}
GET /api/v1/projects
GET /api/v1/projects/
GET /api/v1/projects/{project_id}
GET /api/v1/projects/{project_id}/diagram
GET /api/v1/projects/{project_id}/task-tree
GET /api/v1/projects/count
GET /api/v1/projects/debug-filter
GET /api/v1/reports/{task_id}
GET /api/v1/reports/{workflow_id}
GET /api/v1/scenarios/
GET /api/v1/scenarios/{scenario_id}
GET /api/v1/scenarios/{scenario_id}/fullset
GET /api/v1/scenarios/{scenario_id}/preview
GET /api/v1/scenarios/{scenario_id}/status
GET /api/v1/scheduler/agents/health
GET /api/v1/scheduler/logs
GET /api/v1/scheduler/stats
GET /api/v1/search
GET /api/v1/security/alerts
GET /api/v1/security/audit/logs
GET /api/v1/settings/
GET /api/v1/settings/{category}
GET /api/v1/settings/{category}/{key}
GET /api/v1/settings/models
GET /api/v1/settings/sessions
GET /api/v1/skills
GET /api/v1/skills/{skill_id}
GET /api/v1/skills/{skill_id}/files
GET /api/v1/skills/{skill_id}/install-prompt
GET /api/v1/skills/{skill_id}/raw/{filename}
GET /api/v1/solutions
GET /api/v1/solutions/{solution_id}
GET /api/v1/solutions/compare
GET /api/v1/solutions/compare/multi
GET /api/v1/solutions/trend
GET /api/v1/tasks
GET /api/v1/tasks/
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks/{task_id}/activity
GET /api/v1/tasks/{task_id}/attachments
GET /api/v1/tasks/{task_id}/attachments/{attachment_id}/download
GET /api/v1/tasks/{task_id}/comments
GET /api/v1/tasks/{task_id}/context
GET /api/v1/tasks/{task_id}/execution-logs
GET /api/v1/tasks/{task_id}/failure-log
GET /api/v1/tasks/{task_id}/labels
GET /api/v1/tasks/{task_id}/parent
GET /api/v1/tasks/{task_id}/sub-issues
GET /api/v1/tasks/{task_id}/subtasks
GET /api/v1/tasks/{task_id}/verifications
GET /api/v1/tasks/{task_id}/verifier
GET /api/v1/tasks/count
GET /api/v1/tasks/labels/all
GET /api/v1/tasks/statuses
GET /api/v1/traces
GET /api/v1/traces/{task_id}
GET /api/v1/traces/{task_id}/execution-logs
GET /api/v1/traces/{task_id}/step-status
GET /api/v1/vigil/roles/
GET /api/v1/vigil/roles/{role_id}
GET /api/v1/vigil/trust/agents/{agent_id}
GET /api/v1/vigil/trust/agents/{agent_id}/history
GET /api/v1/workflows/
GET /api/v1/workflows/{workflow_id}/dag/conversation/history
GET /api/v1/workflows/{workflow_id}/progress
PATCH /api/v1/agents/{agent_id}/trigger_mode
PATCH /api/v1/artifacts/{artifact_id}
PATCH /api/v1/disputes/{dispute_id}/resolve
PATCH /api/v1/disputes/{dispute_id}/status
PATCH /api/v1/goals/{goal_id}/status
PATCH /api/v1/grasp/cognition/{cognition_id}
PATCH /api/v1/grasp/inject/rules/{rule_id}
PATCH /api/v1/projects/{project_id}
PATCH /api/v1/projects/{project_id}/status
PATCH /api/v1/scenarios/{scenario_id}/status
PATCH /api/v1/tasks/{task_id}
PATCH /api/v1/tasks/{task_id}/block
PATCH /api/v1/tasks/{task_id}/status
PATCH /api/v1/tasks/{task_id}/unblock
PATCH /api/v1/tasks/batch
PATCH /api/v1/traces/{task_id}/complete
PATCH /api/v1/workflows/{workflow_id}/dag
PATCH /api/v1/workflows/{workflow_id}/dag/nodes/{node_id}
POST /api/v1/a2a/broadcast
POST /api/v1/a2a/messages
POST /api/v1/agent-schemes
POST /api/v1/agent-schemes/{scheme_id}/roles
POST /api/v1/agents
POST /api/v1/agents/{agent_id}/heartbeat
POST /api/v1/agents/{agent_id}/match-mcp
POST /api/v1/agents/{agent_id}/tasks/{task_id}/claim
POST /api/v1/agents/{agent_id}/tasks/{task_id}/report
POST /api/v1/artifacts/
POST /api/v1/attachments/{id}/link
POST /api/v1/attachments/upload
POST /api/v1/capabilities/seed
POST /api/v1/disputes/
POST /api/v1/disputes/{dispute_id}/arbitrate
POST /api/v1/disputes/{dispute_id}/discuss
POST /api/v1/evo/distill
POST /api/v1/evo/evolution-events/
POST /api/v1/evo/evolution-events/{event_id}/revert
POST /api/v1/evo/evolve-capabilities
POST /api/v1/evo/genes/
POST /api/v1/evo/genes/extract
POST /api/v1/evo/solidify
POST /api/v1/goals/
POST /api/v1/goals/{goal_id}/activate
POST /api/v1/goals/{goal_id}/assign-tasks
POST /api/v1/goals/{goal_id}/auto-assign
POST /api/v1/goals/{goal_id}/auto-decompose
POST /api/v1/goals/{goal_id}/auto-decompose/preview
POST /api/v1/goals/{goal_id}/converge-iteration
POST /api/v1/goals/{goal_id}/decompose/submit
POST /api/v1/goals/{goal_id}/iterate
POST /api/v1/goals/{goal_id}/iterations/{iter_id}/analysis
POST /api/v1/goals/{goal_id}/iterations/{iter_id}/consensus
POST /api/v1/goals/{goal_id}/iterations/{iter_id}/discuss
POST /api/v1/goals/{goal_id}/mode
POST /api/v1/goals/{goal_id}/pause
POST /api/v1/goals/{goal_id}/pause-iteration
POST /api/v1/goals/{goal_id}/resume
POST /api/v1/goals/{goal_id}/start-iteration
POST /api/v1/goals/{goal_id}/verifier
POST /api/v1/goals/projects/{project_id}/assign-tasks
POST /api/v1/grasp/cognition
POST /api/v1/grasp/inject
POST /api/v1/grasp/inject/dispute-result
POST /api/v1/grasp/inject/rules
POST /api/v1/grasp/inject/task-result
POST /api/v1/grasp/inject/workflow-result
POST /api/v1/grasp/recommend
POST /api/v1/grasp/retrieve
POST /api/v1/grasp/switch-backend
POST /api/v1/grasp/update/{cognition_id}
POST /api/v1/human-input/{input_id}/reject
POST /api/v1/human-input/{input_id}/submit
POST /api/v1/human-review/batch-ruling
POST /api/v1/industry-packs
POST /api/v1/industry-packs/{pack_id}/export
POST /api/v1/industry-packs/{pack_id}/upgrade
POST /api/v1/industry-packs/{pack_id}/validate
POST /api/v1/industry-packs/import
POST /api/v1/internal/tasks/recover-timeout
POST /api/v1/knowledge
POST /api/v1/mcp-servers
POST /api/v1/pack-skills
POST /api/v1/projects/
POST /api/v1/projects/{project_id}/auto-assign
POST /api/v1/projects/{project_id}/pause
POST /api/v1/projects/{project_id}/resume
POST /api/v1/projects/{project_id}/verifier
POST /api/v1/projects/with-deps
POST /api/v1/scenarios/
POST /api/v1/scenarios/{scenario_id}/feedback
POST /api/v1/scenarios/{scenario_id}/instantiate-to-goal
POST /api/v1/scenarios/{scenario_id}/projects
POST /api/v1/scenarios/{scenario_id}/review
POST /api/v1/scenarios/{scenario_id}/tasks
POST /api/v1/scenarios/custom-create
POST /api/v1/scheduler/dependencies/unlock
POST /api/v1/scheduler/tick
POST /api/v1/settings/test-connection
POST /api/v1/solutions
POST /api/v1/solutions/compare
POST /api/v1/tasks/
POST /api/v1/tasks/{task_id}/add-hitl
POST /api/v1/tasks/{task_id}/assign
POST /api/v1/tasks/{task_id}/attachments
POST /api/v1/tasks/{test_id}/comments
POST /api/v1/tasks/{task_id}/complete
POST /api/v1/tasks/{task_id}/fail
POST /api/v1/tasks/{task_id}/labels
POST /api/v1/tasks/{task_id}/pause
POST /api/v1/tasks/{task_id}/progress
POST /api/v1/tasks/{task_id}/restart
POST /api/v1/tasks/{task_id}/resume
POST /api/v1/tasks/{task_id}/retry
POST /api/v1/tasks/{task_id}/review
POST /api/v1/tasks/{task_id}/ruling
POST /api/v1/tasks/{task_id}/sub-issues
POST /api/v1/tasks/{task_id}/takeover
POST /api/v1/tasks/{task_id}/terminate
POST /api/v1/tasks/{task_id}/verifier
POST /api/v1/tasks/{task_id}/verify
POST /api/v1/traces
POST /api/v1/vigil/roles/
POST /api/v1/vigil/trust/agents/{agent_id}
POST /api/v1/workflows/{workflow_id}/activate
POST /api/v1/workflows/{workflow_id}/dag/conversation/reset
POST /api/v1/workflows/{workflow_id}/dag/converse
POST /api/v1/workflows/{workflow_id}/dag/edges
POST /api/v1/workflows/{workflow_id}/dag/nodes
POST /api/v1/workflows/{workflow_id}/dag/reorder
PUT /api/v1/agent-schemes/{scheme_id}
PUT /api/v1/agents/{agent_id}/capability-tags
PUT /api/v1/agents/{agent_id}/config
PUT /api/v1/evo/capsules/{capsule_id}/deprecate
PUT /api/v1/evo/capsules/{capsule_id}/promote
PUT /api/v1/goals/{goal_id}
PUT /api/v1/industry-packs/{pack_id}
PUT /api/v1/knowledge/{entry_id}
PUT /api/v1/mcp-servers/{server_id}
PUT /api/v1/pack-skills/{skill_id}
PUT /api/v1/projects/{project_id}
PUT /api/v1/scenarios/{scenario_id}
PUT /api/v1/scenarios/{scenario_id}/fullset
PUT /api/v1/scenarios/{scenario_id}/projects/{project_id}
PUT /api/v1/scenarios/{scenario_id}/tasks/{task_id}
PUT /api/v1/settings/{category}/{key}
PUT /api/v1/settings/{category}/batch
PUT /api/v1/solutions/{solution_id}
PUT /api/v1/tasks/{task_id}
PUT /api/v1/tasks/{task_id}/depends_on
PUT /api/v1/vigil/roles/{role_id}
"""

for line in endpoint_text.strip().split('\n'):
    parts = line.strip().split(None, 1)
    if len(parts) == 2:
        ALL_ENDPOINTS.append((parts[0], parts[1]))

# Normalize endpoint path for matching
def normalize(path):
    """Convert {param} patterns to generic match."""
    return re.sub(r'\{[^}]+\}', '{*}', path).rstrip('/')

# Scan all test files for endpoint references
TEST_DIR = Path("tests")
test_coverage = {}  # normalized_path -> list of test files

for test_file in TEST_DIR.rglob("test_*.py"):
    try:
        content = test_file.read_text(encoding="utf-8")
    except:
        continue
    
    rel = str(test_file)
    for method, path in ALL_ENDPOINTS:
        # Check if the test file references this endpoint
        # Look for the path (or significant parts of it) in the test content
        path_parts = [p for p in path.split('/') if p and not p.startswith('{')]
        if len(path_parts) >= 2:
            # Check if at least 2 significant path parts appear in the test
            found_parts = sum(1 for p in path_parts if p in content)
            if found_parts >= 2:
                norm = normalize(path)
                if norm not in test_coverage:
                    test_coverage[norm] = []
                test_coverage[norm].append(rel)

# Report
covered = 0
uncovered = []
covered_details = []

for method, path in ALL_ENDPOINTS:
    norm = normalize(path)
    if norm in test_coverage:
        covered += 1
        covered_details.append((method, path, test_coverage[norm]))
    else:
        uncovered.append((method, path))

print(f"TOTAL ENDPOINTS: {len(ALL_ENDPOINTS)}")
print(f"COVERED (by heuristic): {covered} ({covered/len(ALL_ENDPOINTS)*100:.1f}%)")
print(f"UNCOVERED: {len(uncovered)} ({len(uncovered)/len(ALL_ENDPOINTS)*100:.1f}%)")
print()
print("=" * 80)
print("UNCOVERED ENDPOINTS (no test file references them):")
print("=" * 80)
for method, path in uncovered:
    print(f"  {method:7s} {path}")

print()
print("=" * 80)
print("COVERED ENDPOINTS (with test file references):")
print("=" * 80)
for method, path, files in covered_details[:50]:
    print(f"  {method:7s} {path}  -> {', '.join(set(files))[:80]}")
