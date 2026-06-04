// ============================================================
// frontend-api-calls.ts
// 前端调用的所有后端 API 端点（统一清单）
// 自动生成于 2026-05-15 03:35
// 来源：扫描 packages/ui/src 下所有 .ts/.tsx 文件
// ============================================================
// 总计：74 个端点，34 个文件调用
// ============================================================

export interface ApiCall {
  /** HTTP 方法 (从代码推断) */
  method: string;
  /** 端点路径 */
  path: string;
  /** 调用此端点的源文件列表 */
  callers: string[];
}

export const API_CALLS: ApiCall[] = [
  // ===== AGENTS (4) =====
  { method: "GET", path: "/api/v1/agents/", callers: ["pages/AgentList.tsx"] },
  { method: "POST", path: "/api/v1/agents/{id}/heartbeat", callers: ["pages/AgentList.tsx"] },
  { method: "GET", path: "/api/v1/agents/{id}/execution-logs?limit={id}&offset={id}", callers: ["pages/AgentDetailModal.tsx"] },
  { method: "GET", path: "/api/v1/agents/{id}/heartbeat_logs?limit=50", callers: ["pages/AgentDetailModal.tsx"] },

  // ===== ARTIFACTS (2) =====
  { method: "GET", path: "/api/v1/artifacts?{id}", callers: ["pages/ArtifactList.tsx"] },
  { method: "GET", path: "/api/v1/artifacts/{id}/download", callers: ["pages/ArtifactList.tsx"] },

  // ===== CAPABILITIES / SKILLS / MCP (5) =====
  { method: "GET", path: "/api/v1/skills", callers: ["pages/SkillsPage.tsx"] },
  { method: "GET", path: "/api/v1/skills/{id}", callers: ["pages/SkillsPage.tsx"] },
  { method: "GET", path: "/api/v1/skills/{id}/install-prompt", callers: ["pages/SkillsPage.tsx"] },
  { method: "GET", path: "/api/v1/mcp-servers", callers: ["pages/CapabilitiesPage.tsx"] },
  { method: "GET", path: "/api/v1/mcp-servers/{id}/tools", callers: ["pages/CapabilitiesPage.tsx"] },

  // ===== COGNITIVE / GRASP / KNOWLEDGE (7) =====
  { method: "GET", path: "/api/v1/cognitive/entries", callers: ["pages/CognitiveCenter.tsx"] },
  { method: "GET", path: "/api/v1/cognitive/entries?{id}", callers: ["pages/CognitiveCenter.tsx"] },
  { method: "GET", path: "/api/v1/grasp/cognition-assessment/{id}", callers: ["pages/CognitiveAssessment.tsx"] },
  { method: "GET", path: "/api/v1/grasp/injection/logs?page={id}&page_size={id}", callers: ["pages/CognitiveInject.tsx"] },
  { method: "GET", path: "/api/v1/grasp/injection/rules", callers: ["pages/CognitiveInject.tsx"] },
  { method: "GET", path: "/api/v1/grasp/knowledge?q={id}&limit=3", callers: ["pages/CreateGoal.tsx"] },
  { method: "GET", path: "/api/v1/knowledge", callers: ["pages/CognitiveKnowledge.tsx"] },
  { method: "GET", path: "/api/v1/knowledge/{id}", callers: ["pages/CognitiveKnowledge.tsx"] },
  { method: "GET", path: "/api/v1/knowledge?{id}", callers: ["pages/CognitiveKnowledge.tsx"] },

  // ===== DASHBOARD (3) =====
  { method: "GET", path: "/api/v1/dashboard/stats", callers: ["pages/Dashboard.tsx"] },
  { method: "GET", path: "/api/v1/traces?limit=5", callers: ["pages/Dashboard.tsx"] },
  { method: "GET", path: "/api/v1/human-review/stats", callers: ["pages/Dashboard.tsx", "pages/RulingsPage.tsx", "components/NotificationBell.tsx"] },

  // ===== EVENTS / SSE (3) =====
  { method: "GET", path: "/api/v1/events/stream", callers: ["services/eventStream.ts", "services/sse-client.ts"] },
  { method: "GET", path: "/api/v1/events/stream?agent_id={id}", callers: ["services/sse-client.ts"] },
  { method: "GET", path: "/api/v1/events/stream?workflow_id={id}", callers: ["services/eventStream.ts"] },
  { method: "GET", path: "/api/v1/events/pull?{id}", callers: ["services/sse-client.ts"] },

  // ===== GOALS (10) =====
  { method: "POST", path: "/api/v1/goals/{id}/activate", callers: ["pages/GoalDetail.tsx"] },
  { method: "POST", path: "/api/v1/goals/{id}/decompose/submit", callers: ["pages/DecomposePreview.tsx"] },
  { method: "GET", path: "/api/v1/goals/{id}/iteration-status", callers: ["pages/GoalDetail.tsx"] },
  { method: "GET", path: "/api/v1/goals/{id}/iterations", callers: ["pages/GoalDetail.tsx"] },
  { method: "POST", path: "/api/v1/goals/{id}/iterations/{id}/adjust", callers: ["pages/GoalDetail.tsx"] },
  { method: "POST", path: "/api/v1/goals/{id}/iterations/{id}/confirm", callers: ["pages/GoalDetail.tsx"] },
  { method: "POST", path: "/api/v1/goals/{id}/iterations/{id}/discuss", callers: ["pages/GoalDetail.tsx"] },
  { method: "POST", path: "/api/v1/goals/{id}/pause", callers: ["pages/GoalDetail.tsx"] },
  { method: "POST", path: "/api/v1/goals/{id}/resume", callers: ["pages/GoalDetail.tsx"] },

  // ===== HUMAN INPUT (7) =====
  { method: "GET", path: "/api/v1/human-input/pending", callers: ["pages/HumanInputPage.tsx", "pages/HumanInputDashboard.tsx", "components/HumanInputWidget.tsx"] },
  { method: "GET", path: "/api/v1/human-input/stats", callers: ["components/HumanInputStatsWidget.tsx"] },
  { method: "GET", path: "/api/v1/human-input/task/{id}", callers: ["components/HumanInputTaskWidget.tsx"] },
  { method: "GET", path: "/api/v1/human-input/analytics?days={id}", callers: ["pages/HumanInputAnalytics.tsx"] },
  { method: "GET", path: "/api/v1/human-input/{id}", callers: ["pages/HumanInputPage.tsx"] },
  { method: "POST", path: "/api/v1/human-input/{id}/reject", callers: ["pages/HumanInputPage.tsx"] },
  { method: "POST", path: "/api/v1/human-input/{id}/submit", callers: ["pages/HumanInputPage.tsx"] },

  // ===== HUMAN REVIEW (3) =====
  { method: "GET", path: "/api/v1/human-review/pending?{id}", callers: ["pages/RulingsPage.tsx"] },
  { method: "POST", path: "/api/v1/human-review/batch-ruling", callers: ["pages/RulingsPage.tsx"] },

  // ===== PROJECTS (6) =====
  { method: "GET", path: "/api/v1/projects/{id}", callers: ["components/ProjectTaskTree.tsx"] },
  { method: "GET", path: "/api/v1/projects/{id}/diagram", callers: ["pages/ProjectDetail.tsx", "pages/ProjectDiagram.tsx"] },
  { method: "POST", path: "/api/v1/projects/{id}/pause", callers: ["pages/ProjectDetail.tsx"] },
  { method: "POST", path: "/api/v1/projects/{id}/resume", callers: ["pages/ProjectDetail.tsx"] },
  { method: "GET", path: "/api/v1/projects/{id}/task-tree", callers: ["components/ProjectTaskTree.tsx"] },
  { method: "GET", path: "/api/v1/projects?goal_id={id}", callers: ["pages/WorkflowDiagram.tsx"] },

  // ===== SCENARIOS (4) =====
  { method: "GET", path: "/api/v1/scenarios/{id}", callers: ["pages/ScenarioDetail.tsx"] },
  { method: "POST", path: "/api/v1/scenarios/create-for-goal/{id}", callers: ["utils/api.ts"] },
  { method: "POST", path: "/api/v1/scenarios/match-for-goal/{id}", callers: ["utils/api.ts"] },
  { method: "POST", path: "/api/v1/scenarios/{id}/instantiate-workflow", callers: ["utils/api.ts"] },

  // ===== TASKS (10) =====
  { method: "GET", path: "/api/v1/tasks/statuses", callers: ["pages/TaskList.tsx", "pages/TaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/tasks/{id}", callers: ["pages/EnhancedTaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/tasks/{id}/activity", callers: ["pages/TaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/tasks/{id}/activity", callers: ["pages/TaskDetail.tsx", "pages/EnhancedTaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/tasks/{id}/comments", callers: ["pages/TaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/tasks/{id}/execution-logs?limit=50", callers: ["pages/TaskDetail.tsx"] },
  { method: "POST", path: "/api/v1/tasks/{id}/pause", callers: ["pages/TaskDetail.tsx"] },
  { method: "POST", path: "/api/v1/tasks/{id}/resume", callers: ["pages/TaskDetail.tsx"] },
  { method: "POST", path: "/api/v1/tasks/{id}/retry", callers: ["pages/EnhancedTaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/tasks/{id}/verifier", callers: ["pages/TaskDetail.tsx"] },

  // ===== TRACES (2) =====
  { method: "GET", path: "/api/v1/traces/{id}/step-status", callers: ["pages/ExecutionDetail.tsx"] },

  // ===== WORKFLOWS (8) =====
  { method: "GET", path: "/api/v1/workflows", callers: ["pages/ScenarioDetail.tsx", "pages/TaskList.tsx"] },
  { method: "GET", path: "/api/v1/workflows/{id}", callers: ["pages/WorkflowDiagram.tsx"] },
  { method: "POST", path: "/api/v1/workflows/{id}/confirm-and-split", callers: ["pages/WorkflowDiagram.tsx"] },
  { method: "POST", path: "/api/v1/workflows/{id}/dag/converse", callers: ["pages/WorkflowDiagram.tsx"] },
  { method: "POST", path: "/api/v1/workflows/{id}/dag/edges", callers: ["pages/WorkflowDiagram.tsx"] },
  { method: "GET", path: "/api/v1/workflows/{id}/diagram", callers: ["pages/WorkflowDiagram.tsx"] },
  { method: "GET", path: "/api/v1/workflows?task_id={id}&limit=10", callers: ["pages/EnhancedTaskDetail.tsx"] },
  { method: "GET", path: "/api/v1/workflows?{id}", callers: ["pages/TraceViewer.tsx"] },
];

// ============================================================
// 按模块统计
// ============================================================
export const API_CALLS_BY_MODULE = {
  "agents": 4,
  "artifacts": 2,
  "capabilities/skills/mcp": 5,
  "cognitive/grasp/knowledge": 9,
  "dashboard": 3,
  "events/sse": 4,
  "goals": 9,
  "human-input": 7,
  "human-review": 3,
  "projects": 6,
  "scenarios": 4,
  "tasks": 10,
  "traces": 2,
  "workflows": 8,
} as const;

export const TOTAL_FRONTEND_API_CALLS = 74;
export const TOTAL_CALLER_FILES = 34;
